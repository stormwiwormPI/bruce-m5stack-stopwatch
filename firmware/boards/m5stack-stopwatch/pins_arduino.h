#ifndef Pins_Arduino_h
#define Pins_Arduino_h

#include "soc/soc_caps.h"
#include <stdint.h>

#define USB_VID 0x303a
#define USB_PID 0x1001

static const uint8_t TX = 43;
static const uint8_t RX = 44;

static const uint8_t SDA = 11;
static const uint8_t SCL = 10;

// Standard SPI pins required by Arduino SPIClass
static const int8_t SS = -1;
static const int8_t MOSI = -1;
static const int8_t MISO = -1;
static const int8_t SCK = -1;

// Screen setup: 1.75-inch circular AMOLED (466x466)
#ifndef HAS_SCREEN
#define HAS_SCREEN 1
#endif

#ifndef ROUND_SCREEN
#define ROUND_SCREEN 1
#endif

#ifndef NO_TOUCH_FOOTER
#define NO_TOUCH_FOOTER 1
#endif

#ifndef ROTATION
#define ROTATION 0
#endif

#ifndef TFT_WIDTH
#define TFT_WIDTH 466
#endif

#ifndef TFT_HEIGHT
#define TFT_HEIGHT 466
#endif

// Touchscreen Controller: CST820
#ifndef HAS_TOUCH
#define HAS_TOUCH 1
#endif

// Buttons
#ifndef HAS_BTN
#define HAS_BTN 1
#endif

#ifndef HAS_5_BUTTONS
#define HAS_5_BUTTONS 1
#endif

#ifndef BTN_ALIAS
#define BTN_ALIAS "\"Select\""
#endif

#ifndef BTN_PIN
#define BTN_PIN -1
#endif

#ifndef BTN_ACT
#define BTN_ACT LOW
#endif

// Default I2C / HY2.0-4P Grove Port
#ifndef GROVE_SDA
#define GROVE_SDA 48
#define GROVE_SCL 47
#endif

#ifndef SYS_I2C_SDA
#define SYS_I2C_SDA 11
#define SYS_I2C_SCL 10
#endif

// Internal ESP32 RTC is used (no external I2C RTC chip)

// Infrared default pins (external via HY2.0-4P / Grove port)
#ifndef IR_TX_PINS
#define IR_TX_PINS '{{"Grove SDA", GROVE_SDA}, {"Grove SCL", GROVE_SCL}}'
#define IR_RX_PINS '{{"Grove SCL", GROVE_SCL}, {"Grove SDA", GROVE_SDA}}'
#define TXLED GROVE_SDA
#define LED_ON HIGH
#define LED_OFF LOW
#endif

// Radio frequency default pins
#ifndef RF_TX_PINS
#define RF_TX_PINS '{{"Grove SDA", GROVE_SDA}, {"Grove SCL", GROVE_SCL}}'
#define RF_RX_PINS '{{"Grove SCL", GROVE_SCL}, {"Grove SDA", GROVE_SDA}}'
#endif

// SPI default pins
#ifndef SPI_SCK_PIN
#define SPI_SCK_PIN -1
#define SPI_MOSI_PIN -1
#define SPI_MISO_PIN -1
#define SPI_SS_PIN -1
#endif

#ifndef SDCARD_CS
#define SDCARD_CS -1
#define SDCARD_SCK -1
#define SDCARD_MISO -1
#define SDCARD_MOSI -1
#endif

#ifndef CC1101_GDO0_PIN
#define CC1101_GDO0_PIN -1
#define CC1101_SS_PIN -1
#define CC1101_MOSI_PIN -1
#define CC1101_SCK_PIN -1
#define CC1101_MISO_PIN -1
#endif

#ifndef NRF24_CE_PIN
#define NRF24_CE_PIN -1
#define NRF24_SS_PIN -1
#define NRF24_MOSI_PIN -1
#define NRF24_SCK_PIN -1
#define NRF24_MISO_PIN -1
#endif

#ifndef W5500_SS_PIN
#define W5500_SS_PIN -1
#define W5500_MOSI_PIN -1
#define W5500_SCK_PIN -1
#define W5500_MISO_PIN -1
#define W5500_INT_PIN -1
#endif

#endif /* Pins_Arduino_h */
