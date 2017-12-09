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
}

void loop() {
  int i = 0;
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
  char buff[200];
  
  if (Serial.available() > 0) { // when you get some data
    Serial.readBytes(buff, 10); 
  }
  for (i = 0; i<10; i++) {
    sendStrip(patternData[i], 10, 6);
    delay(100);
  }
  
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
