#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <ESP32-HUB75-MatrixPanel-I2S-DMA.h>
#include <vector>

// Wi-Fi and MQTT Configuration
const char* ssid = "WIFI_SSID";
const char* password = "WIFI_PASSWORD";
const char* mqtt_server = "MQTT_SERVER_IP";

WiFiClient espClient;
PubSubClient mqttClient(espClient);

// Matrix Configuration for ESP32 Trinity (64x64)
const int panelWidth = 64;
const int panelHeight = 64;

MatrixPanel_I2S_DMA *dma_display = nullptr;

// Text paging settings
const int MAX_CHARS_PER_LINE = 10;            // (64px - 2px margin) / 6px per char
const unsigned long PAGE_INTERVAL_MS = 5000;  // time each page is shown

// State Variables received from Backend
String currentMode = "weather";
String weatherTemp = "--";
String weatherCondition = "Waiting...";
String weatherLocation = "";

String spotifyArtist = "";
String spotifyTrack = "";
int spotifyProgress = 0;

// Paged text
std::vector<String> artistPages;
std::vector<String> trackPages;
std::vector<String> conditionPages;
int pageIndex = 0;
unsigned long lastPageSwitch = 0;

void renderDisplay();

// Splits text into pages at word boundaries, each page <= maxChars
void splitIntoPages(const String& text, int maxChars, std::vector<String>& pages) {
    pages.clear();
    String line = "";
    int len = text.length();
    int pos = 0;

    while (pos < len) {
        // skip spaces
        while (pos < len && text[pos] == ' ') pos++;
        if (pos >= len) break;

        // read next word
        int start = pos;
        while (pos < len && text[pos] != ' ') pos++;
        String word = text.substring(start, pos);

        // word longer than a full line: has to be split
        while ((int)word.length() > maxChars) {
            if (line.length() > 0) {
                pages.push_back(line);
                line = "";
            }
            pages.push_back(word.substring(0, maxChars));
            word = word.substring(maxChars);
        }

        if (line.length() == 0) {
            line = word;
        } else if ((int)(line.length() + 1 + word.length()) <= maxChars) {
            line += " " + word;
        } else {
            pages.push_back(line);
            line = word;
        }
    }

    if (line.length() > 0) pages.push_back(line);
    if (pages.empty()) pages.push_back("");
}

// Maps a Unicode code point to a single byte the panel font (CP437) can render.
// Known symbols/accents map to their CP437 glyph; accents with no CP437 glyph fall
// back to their base letter; anything else becomes '?'.
char cp437FromCodepoint(uint32_t cp) {
    if (cp < 0x80) return (char)cp;  // plain ASCII

    switch (cp) {
        // Symbols
        case 0x00B0: return (char)0xF8;  // ° degree
        case 0x00A5: return (char)0x9D;  // ¥ yen
        case 0x00A3: return (char)0x9C;  // £ pound
        case 0x20AC: return 'E';         // € euro (no glyph) -> E
        case 0x00A1: return (char)0xAD;  // ¡
        case 0x00BF: return (char)0xA8;  // ¿

        // Latin-1 accented letters present in CP437
        case 0x00C7: return (char)0x80;  // Ç
        case 0x00FC: return (char)0x81;  // ü
        case 0x00E9: return (char)0x82;  // é
        case 0x00E2: return (char)0x83;  // â
        case 0x00E4: return (char)0x84;  // ä
        case 0x00E0: return (char)0x85;  // à
        case 0x00E5: return (char)0x86;  // å
        case 0x00E7: return (char)0x87;  // ç
        case 0x00EA: return (char)0x88;  // ê
        case 0x00EB: return (char)0x89;  // ë
        case 0x00E8: return (char)0x8A;  // è
        case 0x00EF: return (char)0x8B;  // ï
        case 0x00EE: return (char)0x8C;  // î
        case 0x00EC: return (char)0x8D;  // ì
        case 0x00C4: return (char)0x8E;  // Ä
        case 0x00C5: return (char)0x8F;  // Å
        case 0x00C9: return (char)0x90;  // É
        case 0x00E6: return (char)0x91;  // æ
        case 0x00C6: return (char)0x92;  // Æ
        case 0x00F4: return (char)0x93;  // ô
        case 0x00F6: return (char)0x94;  // ö
        case 0x00F2: return (char)0x95;  // ò
        case 0x00FB: return (char)0x96;  // û
        case 0x00F9: return (char)0x97;  // ù
        case 0x00FF: return (char)0x98;  // ÿ
        case 0x00D6: return (char)0x99;  // Ö
        case 0x00DC: return (char)0x9A;  // Ü
        case 0x00E1: return (char)0xA0;  // á
        case 0x00ED: return (char)0xA1;  // í
        case 0x00F3: return (char)0xA2;  // ó
        case 0x00FA: return (char)0xA3;  // ú
        case 0x00F1: return (char)0xA4;  // ñ
        case 0x00D1: return (char)0xA5;  // Ñ

        // Latin Extended-A (e.g. Polish) with no CP437 glyph -> base letter
        case 0x0105: return 'a';  // ą
        case 0x0107: return 'c';  // ć
        case 0x0119: return 'e';  // ę
        case 0x0142: return 'l';  // ł
        case 0x0144: return 'n';  // ń
        case 0x015B: return 's';  // ś
        case 0x017A: case 0x017C: return 'z';  // ź ż
        case 0x0104: return 'A';  // Ą
        case 0x0106: return 'C';  // Ć
        case 0x0118: return 'E';  // Ę
        case 0x0141: return 'L';  // Ł
        case 0x0143: return 'N';  // Ń
        case 0x015A: return 'S';  // Ś
        case 0x0179: case 0x017B: return 'Z';  // Ź Ż

        default: return '?';
    }
}

// Decodes a UTF-8 string into panel-font bytes (one byte per glyph).
String utf8ToCp437(const String& in) {
    String out;
    int i = 0;
    int n = in.length();

    while (i < n) {
        uint8_t c = (uint8_t)in[i];

        if (c < 0x80) { out += (char)c; i++; continue; }

        uint32_t cp;
        int len;
        if ((c & 0xE0) == 0xC0)      { cp = c & 0x1F; len = 2; }
        else if ((c & 0xF0) == 0xE0) { cp = c & 0x0F; len = 3; }
        else if ((c & 0xF8) == 0xF0) { cp = c & 0x07; len = 4; }
        else { out += '?'; i++; continue; }  // invalid lead byte

        if (i + len > n) { out += '?'; break; }

        bool ok = true;
        for (int k = 1; k < len; k++) {
            uint8_t cc = (uint8_t)in[i + k];
            if ((cc & 0xC0) != 0x80) { ok = false; break; }
            cp = (cp << 6) | (cc & 0x3F);
        }
        if (!ok) { out += '?'; i++; continue; }

        out += cp437FromCodepoint(cp);
        i += len;
    }

    return out;
}

void setupMatrix() {
    HUB75_I2S_CFG mxconfig(panelWidth, panelHeight, 1);

    // ESP32 Trinity specific pin mapping
    mxconfig.gpio.r1 = 25;
    mxconfig.gpio.g1 = 26;
    mxconfig.gpio.b1 = 27;
    mxconfig.gpio.r2 = 14;
    mxconfig.gpio.g2 = 12;
    mxconfig.gpio.b2 = 13;
    mxconfig.gpio.a = 23;
    mxconfig.gpio.b = 19;
    mxconfig.gpio.c = 5;
    mxconfig.gpio.d = 17;
    mxconfig.gpio.e = 18;
    mxconfig.gpio.lat = 4;
    mxconfig.gpio.oe = 15;
    mxconfig.gpio.clk = 16;

    dma_display = new MatrixPanel_I2S_DMA(mxconfig);
    dma_display->begin();
    dma_display->setBrightness8(64);
    dma_display->setTextWrap(false);  // we handle wrapping ourselves
    dma_display->cp437(true);         // use the full CP437 glyph table (°, accents, etc.)
    dma_display->clearScreen();
}

void setupWifi() {
    delay(10);
    Serial.println();
    Serial.print("Connecting to ");
    Serial.println(ssid);

    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\nWiFi connected.");
}

void callback(char* topic, byte* payload, unsigned int length) {
    StaticJsonDocument<512> doc;
    DeserializationError error = deserializeJson(doc, payload, length);

    if (error) {
        Serial.print(F("deserializeJson() failed: "));
        Serial.println(error.f_str());
        return;
    }

    currentMode = doc["mode"] | "weather";

    if (currentMode == "weather") {
        // Board composes the "°C" suffix itself; temp arrives as a number.
        if (!doc["temp"].isNull()) {
            int t = doc["temp"] | 0;
            weatherTemp = String(t) + (char)0xF8 + "C";  // 0xF8 = ° in CP437
        } else {
            weatherTemp = "--";
        }

        weatherLocation = utf8ToCp437(doc["location"].as<String>());

        String newCondition = utf8ToCp437(doc["condition"].as<String>());
        if (newCondition != weatherCondition) {
            weatherCondition = newCondition;
            splitIntoPages(weatherCondition, MAX_CHARS_PER_LINE, conditionPages);
            pageIndex = 0;
            lastPageSwitch = millis();
        }
    } else if (currentMode == "spotify") {
        String newArtist = utf8ToCp437(doc["artist"].as<String>());
        String newTrack = utf8ToCp437(doc["track_name"].as<String>());

        // Only rebuild pages when the song actually changed
        if (newArtist != spotifyArtist || newTrack != spotifyTrack) {
            spotifyArtist = newArtist;
            spotifyTrack = newTrack;
            splitIntoPages(spotifyArtist, MAX_CHARS_PER_LINE, artistPages);
            splitIntoPages(spotifyTrack, MAX_CHARS_PER_LINE, trackPages);
            pageIndex = 0;
            lastPageSwitch = millis();
        }

        spotifyProgress = doc["progress"] | 0;
    }

    renderDisplay();
}

void reconnectMqtt() {
    while (!mqttClient.connected()) {
        Serial.print("Attempting MQTT connection...");
        if (mqttClient.connect("ESP32TrinityClient")) {
            Serial.println("connected");
            mqttClient.subscribe("home/led/display/state");
        } else {
            Serial.print("failed, rc=");
            Serial.print(mqttClient.state());
            Serial.println(" try again in 5 seconds");
            delay(5000);
        }
    }
}

// Prints text horizontally centered on the 64 px panel (6 px per char)
void printCentered(const String& text, int y, uint16_t color) {
    int w = text.length() * 6 - 1;   // last char has no trailing gap
    if (w < 0) w = 0;
    int x = (panelWidth - w) / 2;
    if (x < 0) x = 0;

    dma_display->setCursor(x, y);
    dma_display->setTextColor(color);
    dma_display->print(text);
}

// Artist + track name (current page of each)
void drawTrackText() {
    dma_display->setTextSize(1);

    String artistLine = artistPages.empty() ? "" : artistPages[pageIndex % artistPages.size()];
    String trackLine  = trackPages.empty()  ? "" : trackPages[pageIndex % trackPages.size()];

    printCentered(artistLine, 1,  dma_display->color565(70, 120, 235));  // artist blue
    printCentered(trackLine,  10, dma_display->color565(32, 66, 176));   // title blue
}

// CD graphic
void drawCD() {
    const int cx = 32;
    const int cy = 35;   // one row higher than before
    const int r = 15;

    dma_display->drawCircle(cx, cy, r, dma_display->color444(6, 6, 6));
    dma_display->drawCircle(cx, cy, r / 2, dma_display->color444(10, 10, 12));
    dma_display->fillCircle(cx, cy, 3, dma_display->color444(2, 2, 2));
    dma_display->drawCircle(cx, cy, 3, dma_display->color444(15, 15, 15));
}

// Progress bar drawn with pixels: [||||||....]
void drawProgressBar(int percent, int y) {
    const int slots = 10;
    const int pitch = 5;       // px between slot starts (font used 6)
    const int firstX = 9;      // x of first slot
    const int h = 7;           // bar height in rows
    const int leftX = 4;       // left bracket vertical line
    const int rightX = 59;     // right bracket vertical line

    uint16_t blue  = dma_display->color565(32, 66, 176);  // same as title
    uint16_t green = dma_display->color444(0, 15, 0);

    int filled = constrain(percent, 0, 100) / 10;  // 79 -> 7, 80 -> 8

    // Left bracket [
    dma_display->drawFastVLine(leftX, y, h, blue);
    dma_display->drawPixel(leftX + 1, y, blue);
    dma_display->drawPixel(leftX + 1, y + h - 1, blue);

    // Right bracket ]
    dma_display->drawFastVLine(rightX, y, h, blue);
    dma_display->drawPixel(rightX - 1, y, blue);
    dma_display->drawPixel(rightX - 1, y + h - 1, blue);

    // Slots
    for (int i = 0; i < slots; i++) {
        int x = firstX + i * pitch;
        if (i < filled) {
            dma_display->drawFastVLine(x, y, h, green);
        } else {
            dma_display->drawPixel(x, y + h - 1, blue);
        }
    }
}

void renderDisplay() {
    dma_display->clearScreen();

    if (currentMode == "weather") {
        dma_display->setTextColor(dma_display->color444(15, 15, 15));
        dma_display->setTextSize(1);
        dma_display->setCursor(2, 5);
        dma_display->print(weatherLocation);

        dma_display->setCursor(2, 20);
        dma_display->setTextSize(2);
        dma_display->print(weatherTemp);

        dma_display->setTextSize(1);
        dma_display->setCursor(2, 45);
        String condLine = conditionPages.empty()
            ? weatherCondition
            : conditionPages[pageIndex % conditionPages.size()];
        dma_display->print(condLine);

    } else if (currentMode == "spotify") {
        drawTrackText();
        drawCD();
        drawProgressBar(spotifyProgress, 54);
}
}

void setup() {
    Serial.begin(115200);
    setupMatrix();
    setupWifi();

    mqttClient.setServer(mqtt_server, 1883);
    mqttClient.setCallback(callback);
}

void loop() {
    if (!mqttClient.connected()) {
        reconnectMqtt();
    }
    mqttClient.loop();

    // Rotate text pages (only needed if something actually has more than one page)
    bool hasMultiplePages = false;
    if (currentMode == "spotify") {
        hasMultiplePages = (artistPages.size() > 1 || trackPages.size() > 1);
    } else if (currentMode == "weather") {
        hasMultiplePages = (conditionPages.size() > 1);
    }

    if (hasMultiplePages && millis() - lastPageSwitch >= PAGE_INTERVAL_MS) {
        lastPageSwitch = millis();
        pageIndex++;
        renderDisplay();
    }
}
