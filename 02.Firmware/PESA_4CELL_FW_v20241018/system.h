#include "HX711.h"
#include <OneWire.h>
#include <DallasTemperature.h>
#include <stdio.h>
#include <string.h>
#include <EEPROM.h>

const uint8_t sensorsType[1] = {141};   // código balanza de nieve

#define nameNumChars  10


//================================================================================================================
// DEFINICION DE PINES DEL ARDUINO UTILIZADOS
#define LOADCELL_1_DOUT_PIN   6     // Pin de datos provenientes desde módulo HX711
#define LOADCELL_2_DOUT_PIN   7     // Pin de datos provenientes desde módulo HX711
#define LOADCELL_SCK_PIN      5     // Pin de clock entregado a módulo HX711 para funcionar
#define RS485_TX_EN_PIN       4     // Pin que habilita a la RTU para transmitir datos hacia el bus RS-485
#define DS18B20_DATA_PIN      2     // Pin de datos tomados desde el sensor de temperatura
#define LED_BALANZA_PIN       10    // Pin que identifica proceso de obtención de masa




//================================================================================================================
// ESTRUCTURA DE DATOS EN EEPROM
struct SCALE_CONFIG
{  
   bool     default_config;   // booleano que indica si se utiliza la configuración por defecto o no
   uint8_t  rs485_id;         // ID del sensor en red local RS-485
   int      baud_com;      // Multiplicador para el cálculo de comunicacion serial
   float    prop[4];
   float    offset[4];
   char     sensor_name[nameNumChars];   // Nombre que se asignará al sensor en redes virtuales
   int      masa_smpl_avg;    // Cantidad de promedio de mediciones para calcular 
   float    tara;
   float    cal_p;
   float    cal_o;
   int      transmitDelay;
};
SCALE_CONFIG sensorConfig;



//================================================================================================================
// DEFINICIONES PARA SENSOR DE TEMPERATURA
OneWire oneWire(DS18B20_DATA_PIN);
DallasTemperature sensors(&oneWire);


//================================================================================================================
// DEFINICIONES PARA CELDAS DE CARGA
HX711 scale_1;
HX711 scale_2;

//================================================================================================================
// VARIABLES DE MEDICIÓN DE CARGA
long reading_raw[4] ={0,0,0,0};


//================================================================================================================
// DEFINICION DE PUERTOS I/O DEL MCU
void pinInit(void){
  ADCSRA = 0;     // disable ADC. It should be enable at avery analog read to reduce the power consumption.
  pinMode(RS485_TX_EN_PIN,OUTPUT); digitalWrite(RS485_TX_EN_PIN,LOW);
  pinMode(LED_BALANZA_PIN,OUTPUT); digitalWrite(LED_BALANZA_PIN,LOW);
}


//================================================================================================================
// OBTENCIÓN DE DATOS DESDE EEPROM Y CONFIGURACIÓN DE DATOS POR DEFECTO EN CASO DE SER NECESARIO
void eepromInit(void){
  EEPROM.get(0, sensorConfig);
  if(sensorConfig.default_config){
    sensorConfig.baud_com = 9600;
    sensorConfig.prop[0] = 1.;sensorConfig.prop[1] = 1.;sensorConfig.prop[2] = 1.;sensorConfig.prop[3] = 1.;
    sensorConfig.offset[0] = 0.;sensorConfig.offset[1] = 0.;sensorConfig.offset[2] = 0.;sensorConfig.offset[3] = 0.;
    strcpy(sensorConfig.sensor_name,"DFLT");
    sensorConfig.default_config = false;
    sensorConfig.tara = 0;
    sensorConfig.masa_smpl_avg = 1;
    sensorConfig.cal_p = 1;
    sensorConfig.cal_o = 0;
    sensorConfig.rs485_id = 141;
    sensorConfig.transmitDelay = 0;
    EEPROM.put(0, sensorConfig);
  }
}





//================================================================================================================
// Inicialización celdas de carga
void loadCellInit(void){
  scale_1.begin(LOADCELL_1_DOUT_PIN, LOADCELL_SCK_PIN);
  scale_2.begin(LOADCELL_2_DOUT_PIN, LOADCELL_SCK_PIN);
  scale_1.read();
  scale_2.read();
  scale_1.power_down();
  scale_2.power_down();
}


//================================================================================================================
// Inicialización sensor de temperatura.
void tempInit(void){
  sensors.begin();  
  sensors.setResolution(10);
  delay(10);
  sensors.requestTemperatures();  // lectura dummy para limpiar buffer con ruido del sensor (sólo ocurre con algunos sensores)
}


void setStatusLED(bool ledStatus){
  if(ledStatus){
    digitalWrite(LED_BALANZA_PIN,HIGH);
  }else{
    digitalWrite(LED_BALANZA_PIN,LOW);
  }
}



//================================================================================================================
void leerBalanza(int smpl_avg_qty){
  setStatusLED(true);
  unsigned long timeout_ms = 1000;  // La balanza demora hasta 980mS (en el peor de los casos) en estabiizarse al encender
  unsigned long delay_ms = 1;      // En caso de no encontrar la balanza, se espera 1mS antes de volver a intentarlo
  memset(reading_raw,0,4*sizeof(reading_raw[1]));
  long dummy;

  scale_1.power_up();
  scale_1.set_gain(32);  dummy = scale_1.read_average(1);
  scale_1.set_gain(64);  dummy = scale_1.read_average(1);
  if (scale_1.wait_ready_timeout(timeout_ms, delay_ms)) {
    scale_1.set_gain(32);         // Para leer el canal A del HX711 se requiere aplicar una ganancia de 32 veces al dato
    reading_raw[0] = scale_1.read_average(smpl_avg_qty);  
  
    scale_1.set_gain(64);         // Para leer el canal B del HX711 se requiere aplicar una ganancia de 64 veces al tato
    reading_raw[1] = scale_1.read_average(smpl_avg_qty);
  }
  scale_1.power_down();


  scale_2.power_up();
  scale_2.set_gain(32);  dummy = scale_2.read_average(1);
  scale_2.set_gain(64);  dummy = scale_2.read_average(1);
  if (scale_2.wait_ready_timeout(timeout_ms, delay_ms)) {
    scale_2.set_gain(32);         // Para leer el canal A del HX711 se requiere aplicar una ganancia de 32 veces al dato
    reading_raw[2] = scale_2.read_average(smpl_avg_qty);  
  
    scale_2.set_gain(64);         // Para leer el canal B del HX711 se requiere aplicar una ganancia de 64 veces al tato
    reading_raw[3] = scale_2.read_average(smpl_avg_qty);

  }
  scale_2.power_down();
  setStatusLED(false);  
}



//================================================================================================================
float leerTemperatura(void){
  setStatusLED(true);
  sensors.requestTemperatures();      // Lectura del sensor de temperatura
  float temperatura = sensors.getTempCByIndex(0);
  setStatusLED(false);
  return temperatura;
}


//================================================================================================================
float calculo_masa(int smpl_avg){
  leerBalanza(smpl_avg);
  float masa = 0.;
  for (int i = 0;i < 4; i++){
    masa = masa + float(sensorConfig.prop[i]) * float(reading_raw[i]) + sensorConfig.offset[i];
  }
  return masa;
}


//================================================================================================================
String sensorsConnected(void){
  String msj = "";
  for(int i = 0; i < sizeof(sensorsType); i++){
    msj += String(sensorsType[i]);
    if(i < sizeof(sensorsType)-1) msj += ",";
  }
  return msj;
}
