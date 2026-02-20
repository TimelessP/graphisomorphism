#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

__attribute__((noinline)) static int shared_score(int seed) {
    int acc = seed;
    for (int i = 0; i < 40; ++i) {
        if ((acc & 1) == 0) {
            acc = (acc >> 1) + 7;
        } else {
            acc = (acc * 3) - 5;
        }

        if (acc > 2000) {
            acc -= 333;
        }
        if (acc < -2000) {
            acc += 777;
        }
    }
    return acc;
}

__attribute__((noinline)) static int shared_mix(const char *text) {
    int total = 0;
    for (size_t i = 0; text[i] != '\0'; ++i) {
        unsigned char value = (unsigned char)text[i];
        if ((value % 2) == 0) {
            total += (int)value;
        } else {
            total -= (int)value;
        }

        if (total > 5000) {
            total = total / 2;
        }
    }
    return total;
}

__attribute__((noinline)) static int unique_beta(int x) {
    int out = x;
    for (int i = 0; i < 30; ++i) {
        unsigned ux = (unsigned)out;
        if (ux > 20000u) {
            out -= (i + 5);
        } else if (ux < 150u) {
            out += (i * 4);
        } else {
            out ^= (i << 1);
        }

        if ((out & 8) != 0 && i > 10) {
            out -= 9;
        }
    }

    return out;
}

int main(int argc, char **argv) {
    const char *input = argc > 1 ? argv[1] : "beta-demo";
    int seed = argc > 2 ? atoi(argv[2]) : 123;

    int r1 = shared_score(seed);
    int r2 = shared_mix(input);
    int r3 = unique_beta(seed + r2);

    if (r1 > r3) {
        printf("prog_b high %d\n", r1 - r3);
    } else {
        printf("prog_b low %d\n", r3 - r1);
    }

    return (r1 ^ r2 ^ r3) & 0xFF;
}
