/* SOLIDWORKS CheckSum32: reflected CRC polynomial, complemented EACH byte.
 * This differs from standard CRC32's final-only complement. See PROGRESS.md.
 */
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>

int main(int argc, char **argv)
{
    uint32_t table[256], checksum = UINT32_MAX;
    unsigned char buffer[65536];
    size_t count;
    FILE *input;
    if (argc != 2) return 2;
    for (unsigned i = 0; i < 256; ++i) {
        uint32_t value = i;
        for (unsigned bit = 0; bit < 8; ++bit)
            value = (value >> 1) ^ ((value & 1) ? UINT32_C(0xedb88320) : 0);
        table[i] = value;
    }
    input = fopen(argv[1], "rb");
    if (!input) return 2;
    while ((count = fread(buffer, 1, sizeof(buffer), input)) != 0)
        for (size_t i = 0; i < count; ++i)
            checksum = ~((checksum >> 8) ^ table[(checksum ^ buffer[i]) & 255]);
    if (ferror(input)) { fclose(input); return 2; }
    if (fclose(input)) return 2;
    printf("%" PRIu32 "\n", checksum);
    return 0;
}
