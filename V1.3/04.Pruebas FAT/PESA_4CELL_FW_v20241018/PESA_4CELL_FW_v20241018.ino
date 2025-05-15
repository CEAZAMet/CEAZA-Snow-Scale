/*El presente Sketch corresponde al Firmware de la
 * unidad remota (RTU) asociada al peso de nieve
 * para ser enlazada por medio de comunicación serial
 * sobre RS-485 hacia la una unidad maestra que se pueda
 * comunicar a 9600bps con el protocolo propio del sensor.
 * 
 * El peso se obtiene desde cuatro celdas de carga de 
 * hasta 20Kg cada una a traves de dos módulos HX711 conectados 
 * al MCU del sensor.
 * 
 * Dado que la temperatura puede afectar a las mediciones
 * también se ha equiado el equipo con un sensor de temperatura DS18B20
 * 
 * Se recomienda cargar el presente FW por medio del terminal
 * ICSP con el objetivo de minimizar el tiempo de inicio
 * del microcontrolador. Este tipo de carga de FW borra el 
 * contenido de la EEPROM y además impide actualizar el FW 
 * por medio del puerto serial.
 * 
 * El desarrollo está considerado sobre una tarjeta
 * Arduino Pro Mini de 3.3V y 8MHz con el objetivo de
 * minimizar el consumo eléctrico de la RTU (< 20mA).
 *
 * Firmware escrito por Adrián Gallardo, CEAZA.
 * 
 * V20211006.1: Se adapta para medición de solo una celda en el canal A
 * V20221128.1: se adapta cógigo para unidad con 2 HX711
 * V20221213.1: se corrige implementación de tara, se muestran 7 decimales de valores proporcionales de calibración al ser consultados
 * V20221227.1: se corrige calculo de tara
 * V20230201.1: Se elimina get_masa, get_temp, get_tare, get_prop, get_offset, get_fw, get_smpl_avg, get_name. Toda la info se despliega con get_config
 *              Se incluye get_w, correspondiente a la masa que se entregará al usuario
 *              Se incluye get_t
 *              Se incluye funcion get_rw, que entrega medición de masa sin calibracion de usuario
 *              Se incluye set_prop, para calibracion de usuario
 *              Se incluye set_offset, para calibración de usuario
 *              Se incluye at
 *              Se corrige calculo de tara
 * V20230228.1: Se apagan los ADC luego de inicialización para ahorrar energía
 * V20230321.1: Se agrega función get_sens como parte del protocolo CEAZA para identificación automática de sensores
 * V20230605.1: Se incluye set_txd para agregar un delay en mS antes de la respuesta. Esto hace comptible con anemómetro sónico p.ej: <141,set_txd,1000>
 *              Se incluye id por defecto 141
 *              Se incluye información de modelo de procesador y parámetro de txd en el despliegue de get_config
 * V20230913.1: Se reconoce comandos sin importar si las letras son mayusculas o minúsculas
 *              Se actualiza muestra de parámetros de conficuración para simplificar interpretación por máquinas
 * V20240529.1: Se agrega na lectura dumy de sensor de temperatura para corregir primera lectura erróea al energizar la unidad.
 *              Se segenta el código para mejor entendimiento.
 *              Se optimiza procesamiento de mensajes seriales. Ahora reconoce comandos indistintamente con mayusculas o minúsculas.
  v20241002 Se cambia la funcion check messages para que funcione 
  v20241018 Se elimina la funcion GET_W4 y se cambia por GET_W4X en donde se agrega el peso total aparte del de las 4
  v20241021 Se solicita solo 1 vez el peso en la funcion GET_W4X
 */
#define FIRMWARE_VERSION "V20241018"

#include "system.h"
#include "com.h"
#include "cmd.h"

void setup() {
  pinInit();
  setStatusLED(true);
  eepromInit();
  rs485Init();
  loadCellInit();
  tempInit();
  setStatusLED(false);
}

//================================================================================================================
// PROGRAMA PRINCIPAL
void loop() {
  
  checkComMessage();
}