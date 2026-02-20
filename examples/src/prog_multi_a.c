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

__attribute__((noinline)) static int unique_left(int x) {
    int out = x;
    for (int i = 0; i < 28; ++i) {
        if (i < 8) {
            out += i;
        } else if (i > 20) {
            out ^= (i << 2);
        } else {
            out -= (i * 5);
        }
    }
    return out;
}

int main(int argc, char **argv) {
    int seed = argc > 1 ? atoi(argv[1]) : 77;
    int a = repeated_shared_one(seed);
    int b = unique_left(seed + a);
    int c = repeated_shared_two(seed + b);
    printf("A:%d\n", a + b + c);
    return (a ^ b ^ c) & 0xFF;
}
