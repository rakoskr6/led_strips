#include <FastLED.h>

#define LED_PIN               5
#define NUM_LEDS              300
#define SERIAL_BUFF_SIZE      (NUM_LEDS*3 + 1) // +1 for the command  
#define BRIGHTNESS            255 // currently not used
#define LED_TYPE              WS2812B
#define COLOR_ORDER           GRB
#define ENABLE_DEBUG_MSGS     0
#define DELAY                 100

uint8_t startIndex = 0;

CRGB leds[NUM_LEDS];

void fillLEDs(char r, char g, char b);
void FillLEDsWithChristmas(); // Alternates red and green LEDs 

// Color Palette stuff
CRGBPalette16 currentPalette;
TBlendType    currentBlending;
extern CRGBPalette16 ChristmasPalette;
extern const TProgmemPalette16 ChristmasPalette_p PROGMEM;


void setup() {
  delay(500); // power-up safety delay
  FastLED.addLeds<LED_TYPE, LED_PIN, COLOR_ORDER>(leds, NUM_LEDS).setCorrection( TypicalLEDStrip );
  FastLED.setBrightness(BRIGHTNESS);
  currentPalette = ChristmasPalette_p;
  currentBlending = LINEARBLEND;
  
  Serial.begin(500000); // Set baud rate
  
  // Startup sequence to indicate bootup complete
  fillLEDs(0, 0, 0);
  delay(200);
  FillLEDsWithChristmas();
  delay(200);
  fillLEDs(0, 0, 255);
  delay(200);
  FillLEDsWithChristmas();
  delay(200);
  fillLEDs(0, 0, 0);

  
  //if (ENABLE_DEBUG_MSGS) {
    Serial.println("Program Started");
    Serial.println(SERIAL_BUFF_SIZE);
  //}
}


void fillLEDs(char r, char g, char b) {
  for (int i=0; i < NUM_LEDS; i++) {
    leds[i].setRGB(r, g, b);
   }
  FastLED.show();
}


void FillLEDsWithChristmas() { // Alternates red and green LEDs 
  int x = 0;
  for (int i=0; i < NUM_LEDS; i++) {
    if (x == 0) {
      leds[i].setRGB(255, 0, 0);
      x = 1;
    }
    else {
      leds[i].setRGB(0, 255, 0);
      x = 0;
    }
   }
  FastLED.show();
}


void fillLEDsFromPaletteColors( uint8_t colorIndex)
{
    uint8_t brightness = 255;
    
    for( int i = 0; i < NUM_LEDS; i++) {
        leds[i] = ColorFromPalette( currentPalette, colorIndex, brightness, currentBlending);
        colorIndex += 3;
    }
    FastLED.show();
}


/* Reads the buffer in order to handle the command byte  
 *  and execute the desired functionality
 */
void processBuffer(char *buff) {
  int count = 0;
  int i = 1, j = 2, k = 3;
  int red, green, blue;
  char command = buff[0];
  
  if (command == 0x1) { // global color mode
    red = buff[i];
    green = buff[j];
    blue = buff[k];
    fillLEDs(red, green, blue);    
  }
  else if (command == 0x02) { //color palette 
    fillLEDsFromPaletteColors(startIndex);
  }
  else { // normal mode
    while (count < (NUM_LEDS)) {
      red = buff[i];
      green = buff[j];
      blue = buff[k];
  
            if (ENABLE_DEBUG_MSGS == 1) {
              Serial.print("Count = ");
              Serial.println(count);
              Serial.print("LED i = " );
              Serial.println(red);
              Serial.print("LED j = ");
              Serial.println(green);
              Serial.print("LED k = ");
              Serial.println(blue);
            }
  
      leds[count].setRGB(red, green, blue);
  
      i += 3;
      j += 3;
      k += 3;
      count++;
      }
  
    FastLED.show();
  }

}

  int buffPos = 0;
  int numBytesToRead;
  
void loop() {
  char serialBuff[SERIAL_BUFF_SIZE];
  char ch;
  
  startIndex = startIndex + 1;  

  while (Serial.available() > 0) { // when serial buffer has data
    ch = Serial.read(); // read one byte 
   
    if (buffPos == 0 && ch == 0x1) { //global color mode
      numBytesToRead = 4 - 1;
    }
    else if (buffPos == 0 && ch == 0x2) { // palette mode
      numBytesToRead = 1 - 1; 
    }
    else if (buffPos == 0) { // default to individually addressable LEDs
      numBytesToRead = SERIAL_BUFF_SIZE - 1;
    }

    
    if (buffPos == numBytesToRead) {
      serialBuff[buffPos] = ch; // grab last needed byte
      
      if (ENABLE_DEBUG_MSGS == 1) {
        Serial.print("serialBuff[");
        Serial.print((buffPos ));
        Serial.print("] = ");
        Serial.println(serialBuff[(buffPos)]);       
      }
      //Serial.println("Clear buffer");
      processBuffer(serialBuff);
      buffPos = 0;
    } 
    else {
      serialBuff[buffPos] = ch; // Store received byte   
      buffPos++; // Move to next position in buffer
      if (ENABLE_DEBUG_MSGS == 1) {
        Serial.print("serialBuff[");
        Serial.print((buffPos ));
        Serial.print("] = ");
        Serial.println(serialBuff[(buffPos)]);       
      }   
    }

  }

}




// This example shows how to set up a static color palette
// which is stored in PROGMEM (flash), which is almost always more
// plentiful than RAM.  A static PROGMEM palette like this
// takes up 64 bytes of flash.
const TProgmemPalette16 ChristmasPalette_p PROGMEM =
{
    CRGB::White,
    CRGB::Red,
    CRGB::Red,
    CRGB::Red,
    CRGB::Red,
    CRGB::Red,
    CRGB::Red,
    CRGB::White,
    
    CRGB::Green,
    CRGB::Green,
    CRGB::Green,
    CRGB::Green,
    CRGB::Green,
    CRGB::Green,
    CRGB::White,
   
};
