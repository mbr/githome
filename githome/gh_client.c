#include <libgen.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <sys/un.h>


#define MAX_ARGS 32
#define ARG_LEN 1024


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


void send_all_fail(int socket, void *buf, size_t len) {
  if (! send_all(socket, buf, len)) {
    perror("send_all");
    exit(EXIT_FAILURE);
  }
}


int readline(int fd, char *buf, size_t n) {
  ssize_t r, total = 0;

  do {
    r = read(fd, buf, 1);

    if (r == -1) {
        if (errno == EINTR) continue;  /* retry */
        return -1;
    }

    if (r == 1) {
      if (*buf == '\n') break;
      ++buf;
      total += r;
    }
  } while(r && total + 1 < n);

  *buf = '\0';

  return total;
}


void print_args(int argc, char **argv) {
  int i;

  for(i = 0; i < argc; ++i)
    printf("%s\n", argv[i]);
}


void* fmalloc(size_t size) {
  void* p = malloc(size);
  if (! p) {
    perror("malloc");
    exit(EXIT_FAILURE);
  }

  return p;
}


void exit_error(char *msg) {
  fprintf(stderr, "%s\n", msg);
  exit(EXIT_FAILURE);
}


void check_status(int fd) {
  char buffer[1024];
  ssize_t r;

  r = readline(fd, buffer, sizeof(buffer));

  if (r == 0)
    exit_error("remote end closed connection unexpectedly\n");

  if (r < 0)
    exit_error("read status");

  if (r < 2)
    exit_error("response too short");

  if (! strncmp("E ", buffer, 2))
    exit_error(buffer+2);

  if (strncmp("OK", buffer, 2))
    exit_error("unexpected reply");

  // we got an OK!
}


int connect_socket(char *path) {
  int sock;
  struct sockaddr_un srv;

  sock = socket(AF_UNIX, SOCK_STREAM, 0);
  if (sock < 0) {
    perror("failed to open socket");
    return -1;
  }

  srv.sun_family = AF_UNIX;
  strncpy(srv.sun_path, path, sizeof(srv.sun_path) - 1);

  if (connect(sock, (struct sockaddr*) &srv, sizeof(srv)) < 0) {
    close(sock);
    return -1;
  }

  return sock;
}


int main(int argc, char **argv) {
  int sock, c, dry_run = 0;

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
    exit(EXIT_FAILURE);
  }

  sock = connect_socket(argv[optind]);
  if (sock < 0) {
    perror("connect_socket");
    return EXIT_FAILURE;
  }

  int i;
  for (i = optind+1; i < argc; ++i) {
    send_all_fail(sock, argv[i], strlen(argv[i]));
    send_all_fail(sock, "\n", 1);
  }

  /* read status */
  check_status(sock);

  /* read returned arguments */
  /* extra space for zero-termination of argument list */
  char **nargv = fmalloc(sizeof(char*) * (MAX_ARGS + 1));

  ssize_t r;
  int nargc = 0;

  for(;;) {
    char *buffer = fmalloc(sizeof(char) * ARG_LEN);

    r = readline(sock, buffer, ARG_LEN);

    if (r == 0) break;

    if (r < 0) {
      perror("failed to read");
      return EXIT_FAILURE;
    };

    nargv[nargc] = buffer;
    ++nargc;
  };
  nargv[nargc] = (char*) 0;
  close(sock);

  if (dry_run) {
    print_args(nargc, nargv);
  } else {
    /* ensure there are enough arguments to execute */
    if (nargc < 1)
      exit_error("validation failed; too few arguments returned");

    /* finally, execute program */
    if (! execvp(nargv[0], nargv)) {
       perror("execvp");
       return EXIT_FAILURE;
    }
  }

  return 0;
}
