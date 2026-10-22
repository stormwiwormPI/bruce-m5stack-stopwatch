#include "core/bus_HAL.h"
#include "core/powerSave.h"
#include "core/utils.h"
#include <M5Unified.h>
#include <interface.h>

static unsigned long bootGraceUntil = 0;

/***************************************************************************************
** Function name: _setup_gpio()
** Location: main.cpp
** Description:   Initial setup for M5Stack StopWatch Dev Kit
***************************************************************************************/
void _setup_gpio() {
    M5.begin();

    // Track I2C bus for Bruce hardware abstraction
    setSysI2CBus(M5.In_I2C.getPort() == I2C_NUM_1 ? &Wire1 : &Wire);

#if defined(HAS_RTC)
    _rtc.setWire(getSysI2CBus());
#endif

    bruceConfig.colorInverted = 0;
    bootGraceUntil = millis() + 2000; // Ignore power-on transient presses for 2 seconds
}

/***************************************************************************************
** Function name: _post_setup_gpio()
** Location: main.cpp
** Description:   Second stage GPIO setup
***************************************************************************************/
void _post_setup_gpio() {
    uint8_t b = (bruceConfig.bright > 100) ? 100 : bruceConfig.bright;
    uint8_t mapped = (b == 0) ? 0 : (uint8_t)((b * 255) / 100);
    if (b > 0 && mapped < 30) mapped = 30;
    M5.Display.setBrightness(mapped);
}

/***************************************************************************************
** Function name: getBattery()
** Location: display.cpp
** Description:   Delivers battery percentage from 0-100%
***************************************************************************************/
int getBattery() {
    int percent = M5.Power.getBatteryLevel();
    return (percent < 0) ? 0 : (percent >= 100) ? 100 : percent;
}

/***************************************************************************************
** Function name: isCharging()
** Description:   Determines if the device is currently charging
***************************************************************************************/
bool isCharging() {
    return M5.Power.isCharging() || (M5.Power.getBatteryCurrent() > 0);
}

/*********************************************************************
** Function: setBrightness
** Location: settings.cpp
** Maps Bruce 0-100 brightness to LovyanGFX 0-255 scale
**********************************************************************/
void _setBrightness(uint8_t brightval) {
    uint8_t b = (brightval > 100) ? 100 : brightval;
    uint8_t mapped = (b == 0) ? 0 : (uint8_t)((b * 255) / 100);
    if (b > 0 && mapped < 30) mapped = 30;
    M5.Display.setBrightness(mapped);
}

/*********************************************************************
** Function: InputHandler
** Location: main.cpp
** Navigation Mapping:
** - Top Left Button (BtnA):
**     1 Click  : Go Left / Prev
**     2 Clicks : Go Down
**     Hold >500ms : Go Back / Esc
** - Top Right Button (BtnB):
**     1 Click  : Go Right / Next
**     2 Clicks : Go Up
**     Hold >500ms : Click / Select / Press
** - Power button click : Go Back / Esc
** - Both buttons together : Go Back / Esc
** - CST820 Touchscreen:
**     Tap center : Select
**     Tap left   : Prev
**     Tap right  : Next
**     Tap top    : Back
**     Tap bottom : Next
**     Flick left/right : Next/Prev
**     Flick down : Back
**     Full coordinate tracking for on-screen keyboard
**********************************************************************/
void InputHandler(void) {
    checkPowerSaveTime();

    if (!trylockSysI2CBus()) return; // Concurrency protection
    M5.update();
    unlockSysI2CBus();

    // 0. Boot grace period: prevent false selections during startup
    if (millis() < bootGraceUntil) {
        SelPress = false;
        PrevPress = false;
        NextPress = false;
        EscPress = false;
        UpPress = false;
        DownPress = false;
        AnyKeyPress = false;
        touchPoint.pressed = false;
        return;
    }

    // 1. Touchscreen input handling
    if (M5.Touch.getCount() > 0) {
        auto t = M5.Touch.getDetail();
        if (t.isPressed()) {
            touchPoint.x = t.x;
            touchPoint.y = t.y;
            touchPoint.pressed = true;
        } else {
            touchPoint.pressed = false;
        }

        // Tap gestures for menus
        if (t.wasClicked()) {
            if (wakeUpScreen()) return;
            AnyKeyPress = true;

            int dx = (int)t.x - 233;
            int dy = (int)t.y - 233;
            // Center tap (within 90px radius): Select
            if (dx * dx + dy * dy < 90 * 90) {
                SelPress = true;
            } else if (t.y < 95) {
                // Top area tap: Back / Esc
                EscPress = true;
            } else if (t.x < 140) {
                // Left area tap: Prev
                PrevPress = true;
            } else if (t.x > 326) {
                // Right area tap: Next
                NextPress = true;
            } else if (t.y > 375) {
                // Bottom area tap: Next / Down
                NextPress = true;
            } else {
                // Default center area: Select
                SelPress = true;
            }
            return;
        }

        // Flick / swipe gestures when gesture completes
        if (t.wasFlicked()) {
            if (wakeUpScreen()) return;
            AnyKeyPress = true;
            if (t.distanceX() > 30) {
                PrevPress = true; // Flick right -> Prev
            } else if (t.distanceX() < -30) {
                NextPress = true; // Flick left -> Next
            } else if (t.distanceY() > 30) {
                EscPress = true; // Flick down -> Back
            } else if (t.distanceY() < -30) {
                NextPress = true; // Flick up -> Next
            }
            return;
        }
    } else {
        touchPoint.pressed = false;
    }

    // 2. Both buttons pressed together -> Back / Esc
    if (M5.BtnA.isPressed() && M5.BtnB.isPressed()) {
        if (wakeUpScreen()) return;
        EscPress = true;
        AnyKeyPress = true;
        return;
    }

    // 3. Power button click -> Back / Esc
    if (M5.BtnPWR.wasClicked()) {
        if (wakeUpScreen()) return;
        EscPress = true;
        AnyKeyPress = true;
        return;
    }

    // 4. Button A (Left Top Button):
    //    1 click  -> Prev (Left)
    //    2 clicks -> Down
    //    Hold (>500ms) -> Esc (Back)
    static bool btnA_holding = false;
    static unsigned long btnA_down_time = 0;
    static unsigned long btnA_release_time = 0;
    static int btnA_clicks = 0;

    if (M5.BtnA.wasPressed()) {
        if (wakeUpScreen()) return;
        btnA_holding = false;
        btnA_down_time = millis();
        AnyKeyPress = true;
    }

    if (M5.BtnA.isPressed()) {
        if (!btnA_holding && (millis() - btnA_down_time > 500)) {
            btnA_holding = true;
            btnA_clicks = 0;
            EscPress = true; // Left hold = BACK / ESC
            AnyKeyPress = true;
        }
    }

    if (M5.BtnA.wasReleased()) {
        if (!btnA_holding) {
            btnA_clicks++;
            btnA_release_time = millis();
        }
    }

    if (btnA_clicks > 0 && (millis() - btnA_release_time > 260)) {
        if (btnA_clicks == 1) {
            PrevPress = true; // Left single click = GO LEFT / PREVIOUS
            AnyKeyPress = true;
        } else if (btnA_clicks == 2) {
            DownPress = true; // Left double click = GO DOWN
            AnyKeyPress = true;
        }
        btnA_clicks = 0;
    }

    // 5. Button B (Right Top Button):
    //    1 click  -> Next (Right)
    //    2 clicks -> Up
    //    Hold (>500ms) -> Sel (Select / Click)
    static bool btnB_holding = false;
    static unsigned long btnB_down_time = 0;
    static unsigned long btnB_release_time = 0;
    static int btnB_clicks = 0;

    if (M5.BtnB.wasPressed()) {
        if (wakeUpScreen()) return;
        btnB_holding = false;
        btnB_down_time = millis();
        AnyKeyPress = true;
    }

    if (M5.BtnB.isPressed()) {
        if (!btnB_holding && (millis() - btnB_down_time > 500)) {
            btnB_holding = true;
            btnB_clicks = 0;
            SelPress = true; // Right hold = CLICK / SELECT
            AnyKeyPress = true;
        }
    }

    if (M5.BtnB.wasReleased()) {
        if (!btnB_holding) {
            btnB_clicks++;
            btnB_release_time = millis();
        }
    }

    if (btnB_clicks > 0 && (millis() - btnB_release_time > 260)) {
        if (btnB_clicks == 1) {
            NextPress = true; // Right single click = GO RIGHT / NEXT
            AnyKeyPress = true;
        } else if (btnB_clicks == 2) {
            UpPress = true; // Right double click = GO UP
            AnyKeyPress = true;
        }
        btnB_clicks = 0;
    }
}

/*********************************************************************
** Function: powerOff
** Location: mykeyboard.cpp
** Turns off the device via M5PM1
**********************************************************************/
void powerOff() {
    M5.Power.powerOff();
}
