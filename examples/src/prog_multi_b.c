#include <stdio.h>
#include <stdlib.h>

__attribute__((noinline)) static int repeated_shared_one(int x) {
    int out = x;
    for (int i = 0; i < 24; ++i) {
        if ((out & 1) == 0) {
            out += i * 3;
        } else {
            out -= i * 2;
        }

        if (out > 600) {
            out -= 111;
        }
        if (out < -600) {
            out += 222;
        }
    }
    return out;
}

__attribute__((noinline)) static int repeated_shared_two(int x) {
    int out = x;
    for (int i = 0; i < 24; ++i) {
        if ((out & 1) == 0) {
            out += i * 3;
        } else {
            out -= i * 2;
        }

        if (out > 600) {
            out -= 111;
        }
        if (out < -600) {
            out += 222;
        }
    }
    return out;
}

__attribute__((noinline)) static int unique_right(int x) {
    int out = x;
    for (int i = 0; i < 28; ++i) {
        unsigned ux = (unsigned)out;
        if (ux > 5000u) {
            out -= (i + 7);
        } else if ((i % 4) == 0) {
            out += (i * 6);
        } else {
            out ^= (i << 1);
        }

        if ((out & 16) != 0 && i > 12) {
            out -= 3;
        }
    }
    return out;
}

int main(int argc, char **argv) {
    int seed = argc > 1 ? atoi(argv[1]) : 77;
    int a = repeated_shared_one(seed);
    int b = unique_right(seed + a);
    int c = repeated_shared_two(seed + b);
    printf("B:%d\n", a + b + c);
    return (a ^ b ^ c) & 0xFF;
}
