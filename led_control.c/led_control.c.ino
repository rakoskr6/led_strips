#define DATA_XX0 (PORTD &= B11110111)
#define DATA_XX1 (PORTD |= B00001000)
#define DATA_X0X (PORTD &= B11011111)
#define DATA_X1X (PORTD |= B00100000)
#define DATA_0XX (PORTD &= B10111111)
#define DATA_1XX (PORTD |= B01000000)

#define DATA_000 (PORTD = B00000000)

#define PIN_SETUP (DDRD |= B11101000) // Uno pins D6, D5, and D3


void sendDataD6(uint32_t data);
void sendDataD5(uint32_t data);
void sendDataD3(uint32_t data);

int sendStrip(uint32_t stripData, int pin);





void setup() {
  // put your setup code here, to run once:
  //pinMode(13,OUTPUT);
  PIN_SETUP;
  DATA_000;
  delayMicroseconds(20);
  Serial.begin(9600);
  pinMode(13, OUTPUT);

  uint32_t blank[10] = {0,0,0,0,0,0,0,0,0,0};
  sendStrip(blank,10,6);
  sendStrip(blank,10,5);
  sendStrip(blank,10,3);

}

void loop() {
  int i = 0, j = 0;
  uint32_t patternData[10][10]={
  {0xff0000,0xff7f00,0xffff00,0x00ff00,0x0000ff,0x6f00ff,0x8f00ff,0x000000,0x000000,0x000000},
  {0x000000,0xff0000,0xff7f00,0xffff00,0x00ff00,0x0000ff,0x6f00ff,0x8f00ff,0x000000,0x000000},
  {0x000000,0x000000,0xff0000,0xff7f00,0xffff00,0x00ff00,0x0000ff,0x6f00ff,0x8f00ff,0x000000},
  {0x000000,0x000000,0x000000,0xff0000,0xff7f00,0xffff00,0x00ff00,0x0000ff,0x6f00ff,0x8f00ff},
  {0x8f00ff,0x000000,0x000000,0x000000,0xff0000,0xff7f00,0xffff00,0x00ff00,0x0000ff,0x6f00ff},
  {0x6f00ff,0x8f00ff,0x000000,0x000000,0x000000,0xff0000,0xff7f00,0xffff00,0x00ff00,0x0000ff},
  {0x0000ff,0x6f00ff,0x8f00ff,0x000000,0x000000,0x000000,0xff0000,0xff7f00,0xffff00,0x00ff00},
  {0x00ff00,0x0000ff,0x6f00ff,0x8f00ff,0x000000,0x000000,0x000000,0xff0000,0xff7f00,0xffff00},
  {0xffff00,0x00ff00,0x0000ff,0x6f00ff,0x8f00ff,0x000000,0x000000,0x000000,0xff0000,0xff7f00},
  {0xff7f00,0xffff00,0x00ff00,0x0000ff,0x6f00ff,0x8f00ff,0x000000,0x000000,0x000000,0xff0000}
  };

  uint32_t patternData2[10][10]={
  {0xff0000,0xff0000,0x0000ff,0x0000ff,0xff0000,0xff0000,0x0000ff,0x0000ff,0xff0000,0xff0000},
  {0x0000ff,0xff0000,0xff0000,0x0000ff,0x0000ff,0xff0000,0xff0000,0x0000ff,0x0000ff,0xff0000},
  {0x0000ff,0x0000ff,0xff0000,0xff0000,0x0000ff,0x0000ff,0xff0000,0xff0000,0x0000ff,0x0000ff},
  {0xff0000,0x0000ff,0x0000ff,0xff0000,0xff0000,0x0000ff,0x0000ff,0xff0000,0xff0000,0x0000ff},
  {0xff0000,0xff0000,0x0000ff,0x0000ff,0xff0000,0xff0000,0x0000ff,0x0000ff,0xff0000,0xff0000},
  {0x0000ff,0xff0000,0xff0000,0x0000ff,0x0000ff,0xff0000,0xff0000,0x0000ff,0x0000ff,0xff0000},
  {0x0000ff,0x0000ff,0xff0000,0xff0000,0x0000ff,0x0000ff,0xff0000,0xff0000,0x0000ff,0x0000ff},
  {0xff0000,0x0000ff,0x0000ff,0xff0000,0xff0000,0x0000ff,0x0000ff,0xff0000,0xff0000,0x0000ff},
  {0xff0000,0xff0000,0x0000ff,0x0000ff,0xff0000,0xff0000,0x0000ff,0x0000ff,0xff0000,0xff0000},
  {0x0000ff,0xff0000,0xff0000,0x0000ff,0x0000ff,0xff0000,0xff0000,0x0000ff,0x0000ff,0xff0000}
  };
  
  uint32_t patternData3[10][10]={
  {0x220000,0x220000,0x000022,0x000022,0x220000,0x220000,0x000022,0x000022,0x220000,0x220000},
  {0x000022,0x220000,0x220000,0x000022,0x000022,0x220000,0x220000,0x000022,0x000022,0x220000},
  {0x000022,0x000022,0x220000,0x220000,0x000022,0x000022,0x220000,0x220000,0x000022,0x000022},
  {0x220000,0x000022,0x000022,0x220000,0x220000,0x000022,0x000022,0x220000,0x220000,0x000022},
  {0x220000,0x220000,0x000022,0x000022,0x220000,0x220000,0x000022,0x000022,0x220000,0x220000},
  {0x000022,0x220000,0x220000,0x000022,0x000022,0x220000,0x220000,0x000022,0x000022,0x220000},
  {0x000022,0x000022,0x220000,0x220000,0x000022,0x000022,0x220000,0x220000,0x000022,0x000022},
  {0x220000,0x000022,0x000022,0x220000,0x220000,0x000022,0x000022,0x220000,0x220000,0x000022},
  {0x220000,0x220000,0x000022,0x000022,0x220000,0x220000,0x000022,0x000022,0x220000,0x220000},
  {0x000022,0x220000,0x220000,0x000022,0x000022,0x220000,0x220000,0x000022,0x000022,0x220000}
  };
  
  
  char serialBuff[200], numBuff[7];
  uint32_t serialPattern[10];// = {0,0,0,0,0,0,0,0,0,0};

  
  if (Serial.available() > 0) { // when you get some data
    Serial.readBytes(serialBuff,60); // get 10 bytes in form 000000111111222222... 
    
    for (i=0; i <= 55; i += 6) {
      numBuff[0] = serialBuff[i];
      numBuff[1] = serialBuff[i+1];
      numBuff[2] = serialBuff[i+2];
      numBuff[3] = serialBuff[i+3];
      numBuff[4] = serialBuff[i+4];
      numBuff[5] = serialBuff[i+5];
      numBuff[6] = '\0';
      serialPattern[i/6] = (uint32_t)strtol(numBuff,NULL,16);

      /*
      // For assistance debugging set LED values uncomment
      Serial.write(serialBuff,60);
      Serial.write("\n\n",2);
      Serial.write("Value at LED #: ");
      Serial.write(numBuff);
      Serial.write("\n",1);
      */
    }

    
    sendStrip(serialPattern,10,6);
    sendStrip(serialPattern,10,5);
    sendStrip(serialPattern,10,3);

  }

  
 
  delay(2);
  
  /*for (i = 0; i<10; i++) {
    sendStrip(patternData3[i], 10, 6);
    sendStrip(patternData3[i], 10, 5);
    sendStrip(patternData3[i], 10, 3);
  }*/


}


int sendStrip(uint32_t *stripData, int stripSize, int pin) {
  int i;

  if (pin == 6) {
    noInterrupts();
    for (i = 0; i < stripSize; i++) {
      sendDataD6(stripData[i]);
    }
    interrupts();
  }
  else if (pin == 5) {
    noInterrupts();
    for (i = 0; i < stripSize; i++) {
      sendDataD5(stripData[i]);
    }
    interrupts();
  }
  else if (pin == 3) {
    noInterrupts();
    for (i = 0; i < stripSize; i++) {
      sendDataD3(stripData[i]);
    }
    interrupts();
  }
  else {
    return -1;
  }

  return 0;
}


void sendDataD6(uint32_t data) { // actually sends the individual strip data
  int i;
  unsigned long j=0x800000; // 1000 0000 0000 0000 0000 0000 (24 bits)
  
 
  for (i=0;i<24;i++)
  {
    if (data & j)
    {
      DATA_1XX; // 28
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");   
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t"); 
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t"); 
      __asm__("nop\n\t"); 
      __asm__("nop\n\t");         
      DATA_0XX;
    }
    else
    {
      DATA_1XX; // 9
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");   
      DATA_0XX;
/*----------------------------*/      
       __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");     
/*----------------------------*/         
    }

    j>>=1;
  }
  
}






void sendDataD5(uint32_t data) { // actually sends the individual strip data
  int i;
  unsigned long j=0x800000; // 1000 0000 0000 0000 0000 0000 (24 bits)
  
 
  for (i=0;i<24;i++)
  {
    if (data & j)
    {
      DATA_X1X; // 28
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");   
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t"); 
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t"); 
      __asm__("nop\n\t"); 
      __asm__("nop\n\t");         
      DATA_X0X;
    }
    else
    {
      DATA_X1X; // 9
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");   
      DATA_X0X;
/*----------------------------*/      
       __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");     
/*----------------------------*/         
    }

    j>>=1;
  }
  
}



void sendDataD3(uint32_t data) { // actually sends the individual strip data
  int i;
  unsigned long j=0x800000; // 1000 0000 0000 0000 0000 0000 (24 bits)
  
 
  for (i=0;i<24;i++)
  {
    if (data & j)
    {
      DATA_XX1; // 28
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");   
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t"); 
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t"); 
      __asm__("nop\n\t"); 
      __asm__("nop\n\t");         
      DATA_XX0;
    }
    else
    {
      DATA_XX1; // 9
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");   
      DATA_XX0;
/*----------------------------*/      
       __asm__("nop\n\t");
      __asm__("nop\n\t");
      __asm__("nop\n\t");     
/*----------------------------*/         
    }

    j>>=1;
  }
  
}
