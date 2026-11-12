#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <time.h>

#define LISTEN_PORT 8381
#define UPSTREAM_HOST "127.0.0.1"
#define UPSTREAM_PORT 8382
#define BUF_SIZE 65536

void generate_ghost_identity(char *uuid_buf, size_t u_len, char *node_buf, size_t n_len) {
    unsigned int r1 = (unsigned int)(rand() % 90000000 + 10000000);
    unsigned int r2 = (unsigned int)(rand() % 9000 + 1000);
    unsigned int r3 = (unsigned int)(rand() % 9000 + 1000);
    unsigned int r4 = (unsigned int)(rand() % 9000 + 1000);
    unsigned int r5 = (unsigned int)(rand() % 900000000000 + 100000000000);
    
    snprintf(uuid_buf, u_len, "%08x-%04x-%04x-%04x-%012llx", r1, r2, r3, r4, (unsigned long long)r5);
    snprintf(node_buf, n_len, "Ghost-Node-%u-x%u", r1 % 900000 + 100000, r2);
}

int forward_to_ghost_relay(const char *json_payload, const char *uuid_str, const char *node_id, char *out_buf, size_t out_maxlen) {
    int sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock < 0) return -1;

    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons(UPSTREAM_PORT);
    inet_pton(AF_INET, UPSTREAM_HOST, &addr.sin_addr);

    if (connect(sock, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        close(sock);
        return -2;
    }

    char req[BUF_SIZE];
    int req_len = snprintf(req, sizeof(req),
        "POST /v1/ghost-route HTTP/1.1\r\n"
        "Host: %s:%d\r\n"
        "Content-Type: application/json\r\n"
        "X-Ghost-UUID: %s\r\n"
        "X-Ghost-Node-ID: %s\r\n"
        "X-Network-Isolation: Namespace-Anonymous\r\n"
        "Content-Length: %zu\r\n"
        "Connection: close\r\n\r\n"
        "%s",
        UPSTREAM_HOST, UPSTREAM_PORT, uuid_str, node_id, strlen(json_payload), json_payload
    );

    if (send(sock, req, req_len, 0) < 0) {
        close(sock);
        return -3;
    }

    size_t total = 0;
    ssize_t n;
    while (total < out_maxlen - 1 && (n = recv(sock, out_buf + total, out_maxlen - 1 - total, 0)) > 0) {
        total += n;
    }
    out_buf[total] = '\0';
    close(sock);
    return (int)total;
}

int main() {
    srand((unsigned int)time(NULL) ^ (unsigned int)getpid());
    int server_fd, new_socket;
    struct sockaddr_in address;
    int opt = 1;
    int addrlen = sizeof(address);

    if ((server_fd = socket(AF_INET, SOCK_STREAM, 0)) == 0) {
        perror("socket failed");
        exit(EXIT_FAILURE);
    }

    setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

    address.sin_family = AF_INET;
    address.sin_addr.s_addr = INADDR_ANY;
    address.sin_port = htons(LISTEN_PORT);

    if (bind(server_fd, (struct sockaddr *)&address, sizeof(address)) < 0) {
        perror("bind failed");
        exit(EXIT_FAILURE);
    }

    if (listen(server_fd, 16) < 0) {
        perror("listen failed");
        exit(EXIT_FAILURE);
    }

    printf("[Ghost RouterDaemon v8.0] Active on 127.0.0.1:%d -> Relay :%d (Dynamic UUID/Node rotation + Connection: close)\n", LISTEN_PORT, UPSTREAM_PORT);
    fflush(stdout);

    char buffer[BUF_SIZE];
    char relay_resp[BUF_SIZE];

    while ((new_socket = accept(server_fd, (struct sockaddr *)&address, (socklen_t*)&addrlen)) >= 0) {
        memset(buffer, 0, sizeof(buffer));
        ssize_t total_read = 0;
        ssize_t r;
        while (total_read < BUF_SIZE - 1 && (r = recv(new_socket, buffer + total_read, BUF_SIZE - 1 - total_read, 0)) > 0) {
            total_read += r;
            char *hdr_end = strstr(buffer, "\r\n\r\n");
            if (hdr_end != NULL) {
                char *cl_ptr = strcasestr(buffer, "Content-Length:");
                if (cl_ptr != NULL) {
                    int content_len = atoi(cl_ptr + 15);
                    size_t body_offset = (size_t)(hdr_end + 4 - buffer);
                    if ((size_t)total_read >= body_offset + (size_t)content_len) {
                        break;
                    }
                } else {
                    break;
                }
            }
        }

        if (total_read > 0) {
            char uuid_str[64];
            char node_id[64];
            generate_ghost_identity(uuid_str, sizeof(uuid_str), node_id, sizeof(node_id));

            char *body_start = strstr(buffer, "\r\n\r\n");
            const char *json_payload = body_start ? (body_start + 4) : "{}";

            memset(relay_resp, 0, sizeof(relay_resp));
            int status = forward_to_ghost_relay(json_payload, uuid_str, node_id, relay_resp, sizeof(relay_resp));

            if (status > 0) {
                char *up_body = strstr(relay_resp, "\r\n\r\n");
                const char *clean_body = up_body ? (up_body + 4) : relay_resp;

                char final_http[BUF_SIZE];
                int final_len = snprintf(final_http, sizeof(final_http),
                    "HTTP/1.1 200 OK\r\n"
                    "Server: GhostRouterD/8.0\r\n"
                    "X-Ghost-UUID: %s\r\n"
                    "X-Ghost-Node-ID: %s\r\n"
                    "X-Network-Isolation: Namespace-Anonymous\r\n"
                    "Content-Type: application/json\r\n"
                    "Content-Length: %zu\r\n"
                    "Connection: close\r\n\r\n"
                    "%s",
                    uuid_str, node_id, strlen(clean_body), clean_body
                );
                send(new_socket, final_http, final_len, 0);
            } else {
                char err_json[512];
                snprintf(err_json, sizeof(err_json),
                    "{\"status\": \"relay_unreachable\", \"error\": \"Ghost relay on port %d not running.\", \"telemetry\": {\"uuid\": \"%s\", \"node_id\": \"%s\"}}",
                    UPSTREAM_PORT, uuid_str, node_id
                );
                char err_http[1024];
                int err_len = snprintf(err_http, sizeof(err_http),
                    "HTTP/1.1 502 Bad Gateway\r\n"
                    "Server: GhostRouterD/8.0\r\n"
                    "X-Ghost-UUID: %s\r\n"
                    "Content-Type: application/json\r\n"
                    "Content-Length: %zu\r\n"
                    "Connection: close\r\n\r\n"
                    "%s",
                    uuid_str, strlen(err_json), err_json
                );
                send(new_socket, err_http, err_len, 0);
            }
        }
        close(new_socket);
    }
    return 0;
}
