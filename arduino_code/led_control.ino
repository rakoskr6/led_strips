#include <FastLED.h>

#define LED_PIN               5
#define NUM_LEDS              453
//#define NUM_LEDS              80
#define SERIAL_BUFF_SIZE      (NUM_LEDS*3 + 1) //+1 for the command  
#define BRIGHTNESS            128
#define LED_TYPE              WS2811
#define COLOR_ORDER           GRB
#define ENABLE_DEBUG_MSGS     0

CRGB leds[NUM_LEDS];


void setup() {
  delay( 3000 ); // power-up safety delay
  FastLED.addLeds<LED_TYPE, LED_PIN, COLOR_ORDER>(leds, NUM_LEDS).setCorrection( TypicalLEDStrip );
  FastLED.setBrightness(  BRIGHTNESS );

  Serial.begin(500000);
  //if (ENABLE_DEBUG_MSGS) {
    Serial.println("Program Started");
    Serial.println(SERIAL_BUFF_SIZE);
  //}
}




void processBuffer(char *buff) {
  int count = 0;
  int i = 1, j = 2, k = 3;
  int red, green, blue;
  int command = buff[0];
  
  //  Serial.print("EOM Received: ");
  //  Serial.println(buff);



  //  if (command == COMMAND_FILL) {
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

  //  }
}

  int buffPos = 0;
  
void loop() {
  char serialBuff[SERIAL_BUFF_SIZE];
  char ch;

  while (Serial.available() > 0) {
    ch = Serial.read();
      
    if (buffPos == (SERIAL_BUFF_SIZE-1)) {
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
      //ch = 0;
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
