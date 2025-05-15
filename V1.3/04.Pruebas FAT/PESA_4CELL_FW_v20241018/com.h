void rs485Init(void){
  Serial.begin(sensorConfig.baud_com);
}

//================================================================================================================
void rs485_send(const String& message){     // Rutina de transmisión de datos por el bus RS-485
  delay(sensorConfig.transmitDelay);
  digitalWrite(RS485_TX_EN_PIN,HIGH);       // Se habilita la RTU como transmisor dentro del bus de datos
  delay(50);
  Serial.print(message);Serial.print(String(F("\n"))); // Se envía la respuesta con los carácteres que la MTU reconocerá como inicio y término del mensaje
  Serial.flush();                           // Tiempo necesario para que se transmita todo el mensaje por el bus RS-485. En caso de reducir la velocidad de comunicación o extender la longitud de los mensajes este velor debe aumentar
  digitalWrite(RS485_TX_EN_PIN,LOW);        // la RTU vuelve a quedar a la escucha de lo que ocurre en el canal.
}


//================================================================================================================
void send_ok(void){
  rs485_send(F("OK"));
}





