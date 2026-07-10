// Receptor OSC minimo: UDP no bloqueante, solo mensajes con un float (",f" o ",i").
// Suficiente para el bridge (bridge/bridge.py); evita depender de oscpack.
// Portable WinSock/POSIX para poder testearlo fuera de Windows.
#pragma once

#include <cstdint>
#include <cstring>
#include <functional>
#include <string>

#ifdef _WIN32
  #include <winsock2.h>
  #include <ws2tcpip.h>
  using socket_t = SOCKET;
  static constexpr socket_t kInvalidSocket = INVALID_SOCKET;
#else
  #include <arpa/inet.h>
  #include <fcntl.h>
  #include <netinet/in.h>
  #include <sys/socket.h>
  #include <unistd.h>
  using socket_t = int;
  static constexpr socket_t kInvalidSocket = -1;
#endif

class OscReceiver {
public:
    using Handler = std::function<void(const char* address, float value)>;

    bool init(uint16_t port) {
#ifdef _WIN32
        WSADATA wsa;
        if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) return false;
#endif
        sock_ = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
        if (sock_ == kInvalidSocket) return false;

        sockaddr_in addr{};
        addr.sin_family = AF_INET;
        addr.sin_port = htons(port);
        addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
        if (bind(sock_, reinterpret_cast<sockaddr*>(&addr), sizeof addr) != 0) {
            close_();
            return false;
        }
#ifdef _WIN32
        u_long nonblock = 1;
        ioctlsocket(sock_, FIONBIO, &nonblock);
#else
        fcntl(sock_, F_SETFL, fcntl(sock_, F_GETFL, 0) | O_NONBLOCK);
#endif
        return true;
    }

    // procesa todos los datagramas pendientes; llama handler por cada mensaje valido
    void poll(const Handler& handler) {
        if (sock_ == kInvalidSocket) return;
        char buf[1024];
        while (true) {
            int n = static_cast<int>(recv(sock_, buf, sizeof buf, 0));
            if (n <= 0) break;  // EWOULDBLOCK o error -> no hay mas datagramas
            parse(buf, n, handler);
        }
    }

    ~OscReceiver() { close_(); }

private:
    socket_t sock_ = kInvalidSocket;

    void close_() {
        if (sock_ != kInvalidSocket) {
#ifdef _WIN32
            closesocket(sock_);
            WSACleanup();
#else
            close(sock_);
#endif
            sock_ = kInvalidSocket;
        }
    }

    static size_t aligned4(size_t n) { return (n + 4) & ~size_t{3}; }  // strlen+1 redondeado a 4

    static void parse(const char* buf, int len, const Handler& handler) {
        if (len < 8 || buf[0] != '/') return;  // no soportamos bundles (#bundle)
        size_t alen = strnlen(buf, len);
        if (alen == static_cast<size_t>(len)) return;
        size_t off = aligned4(alen);
        if (off + 4 > static_cast<size_t>(len) || buf[off] != ',') return;
        const char* tags = buf + off + 1;
        size_t tlen = strnlen(buf + off, len - off);
        size_t argoff = off + aligned4(tlen);
        if (argoff + 4 > static_cast<size_t>(len)) return;

        // primer argumento float o int (big-endian)
        uint32_t be;
        std::memcpy(&be, buf + argoff, 4);
        uint32_t host = ntohl(be);
        float value = 0.0f;
        if (tags[0] == 'f') {
            std::memcpy(&value, &host, 4);
        } else if (tags[0] == 'i') {
            value = static_cast<float>(static_cast<int32_t>(host));
        } else {
            return;
        }
        handler(buf, value);
    }
};
