#define DATA_XX0 (PORTD &= B11110111)
#define DATA_XX1 (PORTD |= B00001000)
#define DATA_X0X (PORTD &= B11011111)
#define DATA_X1X (PORTD |= B00100000)
#define DATA_0XX (PORTD &= B10111111)
#define DATA_1XX (PORTD |= B01000000)

#define DATA_000 (PORTD = B00000000)

#define PIN_SETUP (DDRD |= B11101000) // Uno pins D6, D5, and D3

#define DEBUG 0

void sendDataD6(uint32_t data);
void sendDataD5(uint32_t data);
void sendDataD3(uint32_t data);


int sendStrip(uint32_t *stripData, int stripSize, int pin);

void setup() {
    // put your setup code here, to run once:
    //pinMode(13,OUTPUT);
    PIN_SETUP;
    DATA_000;
    delayMicroseconds(20);
    Serial.begin(115200); // was 9600
    pinMode(13, OUTPUT);

    uint32_t blank[10] = {0,0,0,0,0,0,0,0,0,0};
    sendStrip(blank,10,6);
    sendStrip(blank,10,5);
    sendStrip(blank,10,3);

}

void loop() {
    int i = 0, j = 0, pinNum;  
    char serialBuff[200], numBuff[7], pinNumc;
    uint32_t serialPattern[10];

    if (Serial.available() > 0) { // when you get some data
        Serial.readBytes(serialBuff,41); // get 10 bytes in form 000000111111222222... 
        pinNum = serialBuff[0];
        //pinNum = (int)strtol(pinNumc,NULL,10);
        //pinNum = (int)pinNumc - '0';

        if (DEBUG) {
            //Serial.printf("%x",serialBuff);
            Serial.write("\n",1);

            Serial.write("Send to pin ");
            Serial.write(pinNum+'0');
            //Serial.write("\nthe following values: ");
            //Serial.write(&serialBuff[1],61);
            Serial.write("\n",2);
            for (i=0; i<10; i++) {
                Serial.print(*((uint32_t*)(serialBuff+1+(4*i))),HEX);
            }
            Serial.write("\n",2);
        }

        sendStrip(((uint32_t*)(serialBuff+1)),10,pinNum);

    }
    //delay(20); // give time to send serial (idk if this is necessary)

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
