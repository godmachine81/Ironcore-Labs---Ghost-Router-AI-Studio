#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <time.h>

#define PORT 8381

void generate_random_fingerprint(char *buffer, size_t maxlen) {
    unsigned int r1 = rand() % 900000 + 100000;
    unsigned int r2 = rand() % 90000 + 10000;
    snprintf(buffer, maxlen, "IronCore-Node-%u-x%u", r1, r2);
}

int main() {
    srand(time(NULL));
    int server_fd, new_socket;
    struct sockaddr_in address;
    int opt = 1;
    int addrlen = sizeof(address);

    if ((server_fd = socket(AF_INET, SOCK_STREAM, 0)) == 0) {
        perror("socket failed");
        exit(EXIT_FAILURE);
    }

    if (setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt))) {
        perror("setsockopt");
        exit(EXIT_FAILURE);
    }

    address.sin_family = AF_INET;
    address.sin_addr.s_addr = INADDR_ANY;
    address.sin_port = htons(PORT);

    if (bind(server_fd, (struct sockaddr *)&address, sizeof(address)) < 0) {
        perror("bind failed");
        exit(EXIT_FAILURE);
    }

    if (listen(server_fd, 5) < 0) {
        perror("listen");
        exit(EXIT_FAILURE);
    }

    char buffer[8192] = {0};
    while ((new_socket = accept(server_fd, (struct sockaddr *)&address, (socklen_t*)&addrlen)) >= 0) {
        ssize_t bytes_read = read(new_socket, buffer, sizeof(buffer) - 1);
        if (bytes_read > 0) {
            char ephemeral_id[64];
            generate_random_fingerprint(ephemeral_id, sizeof(ephemeral_id));

            int is_vine = (strstr(buffer, "\"mode\": \"vine\"") != NULL);

            int tokens_utilized = (rand() % 40) + 80;
            int tokens_max = 100000;
            int tokens_remaining = tokens_max - tokens_utilized;

            char json_body[4096];
            if (is_vine) {
                snprintf(json_body, sizeof(json_body),
                    "{\"status\": \"routed_anonymous\", \"mode\": \"vine\", \"title\": \"Foldable Laptop Stand\", \"body\": \"I put this laptop stand through daily use over the past week to see how it holds up during long typing sessions. The aluminum construction feels rigid, and the hinges maintain their angle without slipping under weight. Rubber padding on the base prevents sliding across smooth surfaces, and the open frame allows decent airflow underneath to manage thermals. Adjustments are stiff out of the box but stay secure once positioned. Overall, it performs as expected for workspace ergonomics.\", \"telemetry\": {\"ephemeral_instance_id\": \"%s\", \"tokens_max\": %d, \"tokens_utilized\": %d, \"tokens_remaining\": %d}}",
                    ephemeral_id, tokens_max, tokens_utilized, tokens_remaining
                );
            } else {
                snprintf(json_body, sizeof(json_body),
                    "{\"status\": \"routed_anonymous\", \"mode\": \"general\", \"body\": \"In SDR++, audio demodulation buffers process raw IQ samples by passing them through the selected demodulator (AM, FM, SSB), downsampling to the audio sample rate (typically 48 kHz), and pushing PCM audio frames into a ring buffer. The audio output sink continuously pulls from this ring buffer to feed PortAudio or PulseAudio without underruns.\", \"telemetry\": {\"ephemeral_instance_id\": \"%s\", \"tokens_max\": %d, \"tokens_utilized\": %d, \"tokens_remaining\": %d}}",
                    ephemeral_id, tokens_max, tokens_utilized, tokens_remaining
                );
            }

            char response[8192];
            snprintf(response, sizeof(response), 
                "HTTP/1.1 200 OK\r\n"
                "Server: IronCore-RouterD/2.6.0\r\n"
                "X-IronCore-Instance-ID: %s\r\n"
                "X-Network-Isolation: Namespace-Anonymous\r\n"
                "X-Token-Max: %d\r\n"
                "X-Token-Utilized: %d\r\n"
                "X-Token-Remaining: %d\r\n"
                "Content-Type: application/json\r\n"
                "Connection: close\r\n\r\n"
                "%s",
                ephemeral_id, tokens_max, tokens_utilized, tokens_remaining, json_body
            );
            write(new_socket, response, strlen(response));
        }
        close(new_socket);
        memset(buffer, 0, sizeof(buffer));
    }
    return 0;
}
