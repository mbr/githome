#include <libgen.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <sys/un.h>


int send_all(int socket, void *buf, size_t len) {
  char *ptr = (char*) buf;
  while(len > 0) {
    int n = write(socket, ptr, len);
    if (n < 1) {
      if (n == 0) return -1;
      return n;
    }
    ptr += n;
    len -= n;
  }

  return 0;
}


int readline(int fd, void *buffer, size_t n) {
  char *buf = (char*) buf;
  ssize_t r;

  --n;  /* space for terminating \0 */

  do {
    r = read(fd, buf, 1);

    if (r == -1) {
        if (errno == EINTR) continue;  /* retry */
        return -1;
    }

    if (r == 1) {
      if (*buf == '\n') break;
      ++buf;
      --n;
    }
  } while(r && n);

  *buf = '\0';

  return 0;
}


int main(int argc, char **argv) {
  int sock = socket(AF_UNIX, SOCK_STREAM, 0);
  struct sockaddr_un srv;

  int c, dry_run = 0;

  /* parse options */
  while((c = getopt(argc, argv,  "n")) != -1) {
    switch(c) {
      case 'n':
        dry_run = 1;
      break;
    }
  }

  if (argc < optind + 1) {
    fprintf(stderr, "usage: %s [-n] SOCKET [ARGS]...\n", basename(argv[0]));
    exit(1);
  }

  if (sock < 0) {
    perror("failed to open socket");
    return 1;
  }

  srv.sun_family = AF_UNIX;
  strncpy(srv.sun_path, argv[optind], sizeof(srv.sun_path) - 1);

  if (connect(sock, (struct sockaddr*) &srv, sizeof(srv)) < 0) {
    close(sock);
    perror("failed to connect to server");
    return 1;
  }

  int i;
  for (i = optind+1; i < argc; ++i) {
    if (send_all(sock, argv[i], strlen(argv[i]))) {
      perror("failed to send");
      return 1;
    }

    if (write(sock, "\n", 1) != 1) {
      perror("failed to send");
      return 1;
    }
  }

  close(sock);

  return 0;
}
