//================================================================================================================
void processCmd(int id, String cmd, String par){
  if(id == sensorConfig.rs485_id){ 
    int auxInt;
    float auxFloat;


    if(cmd.equals("SET_BAUD")){
      unsigned long baud = par.toInt();
      if(baud == 1200 || baud == 2400 || baud == 4800 || baud == 9600 || baud == 19200){
        sensorConfig.baud_com = baud;
        EEPROM.put(0, sensorConfig);
        send_ok();
      }else{
        rs485_send(F("ERR: Baud"));
      }

    
    //*************************************************************
    }else if(cmd.equals("SET_ID")){
      auxInt = par.toInt();
      if(auxInt >= 0 && auxInt < 255){
        sensorConfig.rs485_id = auxInt;
        EEPROM.put(0, sensorConfig);
        send_ok();
      }else{
        rs485_send(F("ERR: Addr"));
      }

    
    //*************************************************************
    }else if(cmd.equals("SET_NAME")){
      par.toCharArray(sensorConfig.sensor_name, nameNumChars);
      EEPROM.put(0, sensorConfig);
      send_ok();


    //*************************************************************
    }else if(cmd.equals("GET_CONFIG")){
      String mcuType;
      if ( SIGNATURE_0 == 0x1E || SIGNATURE_0 == 0x00) {
        if ( SIGNATURE_1 == 0x95 && SIGNATURE_2 == 0x0F) {
          mcuType = "ATmega328p";
        } else if ( SIGNATURE_1 == 0x95 && SIGNATURE_2 == 0x16) {
          mcuType = "ATmega328pb";
        } else {
          mcuType = "Unknown Atmel"; 
        }
      } else {
        mcuType = "Unknown";
      }
      
      rs485_send(String(F("\n\nSENSOR CONFIGURATION PARAMETERS\n")));
      rs485_send(String(F("1,RS-485 ID  ,")) + String(sensorConfig.rs485_id));
      rs485_send(String(F("2,S. name    ,")) + String(sensorConfig.sensor_name));
      rs485_send(String(F("3,Com Baud   ,")) + String(sensorConfig.baud_com));
      rs485_send(String(F("4,Tx delay   ,")) + String(sensorConfig.transmitDelay));
      rs485_send(String(F("5,Hardware   ,")) + String(mcuType));
      rs485_send(String(F("6,Firmware   ,")) + String(FIRMWARE_VERSION));
      rs485_send(String(F("7,Instr.Prop ,")) + String(sensorConfig.cal_p,4));
      rs485_send(String(F("8,Instr.Ofst ,")) + String(sensorConfig.cal_o,4));
      rs485_send(String(F("9,Tare       ,")) + String(sensorConfig.tara));
      rs485_send(String(F("10,Sample AVG,")) + String(sensorConfig.masa_smpl_avg));
      rs485_send(String(F("11,Cel. Prop ,")) + String(sensorConfig.prop[0],9) + "," + String(sensorConfig.prop[1],9) + "," + String(sensorConfig.prop[2],9) + "," + String(sensorConfig.prop[3],9));
      rs485_send(String(F("12,Cel. Ofset,")) + String(sensorConfig.offset[0],9) + "," + String(sensorConfig.offset[1],9) + "," + String(sensorConfig.offset[2],9) + "," + String(sensorConfig.offset[3],9));

      
    //*************************************************************
    }else if(cmd.equals("AT")){
      if(par.length() == 0) send_ok();
      
    
    //*************************************************************
    }else if(cmd.equals("GET_W")){
      rs485_send(String(calculo_masa(sensorConfig.masa_smpl_avg) * sensorConfig.cal_p + sensorConfig.cal_o + sensorConfig.tara));   // se responde con el valor obtenido
    
    //*************************************************************
    }
    
     else if(cmd.equals("GET_W4X")){
      leerBalanza(sensorConfig.masa_smpl_avg);
      rs485_send(String(float(sensorConfig.prop[0]) * float(reading_raw[0]) + sensorConfig.offset[0]) + "," + String(float(sensorConfig.prop[1]) * float(reading_raw[1]) + sensorConfig.offset[1]) + "," + String(float(sensorConfig.prop[2]) * float(reading_raw[2]) + sensorConfig.offset[2]) + "," + String(float(sensorConfig.prop[3]) * float(reading_raw[3]) + sensorConfig.offset[3])+","+String(calculo_masa(sensorConfig.masa_smpl_avg) * sensorConfig.cal_p + sensorConfig.cal_o + sensorConfig.tara));
    
    //*************************************************************
    }

    else if(cmd.equals("GET_T")){
      rs485_send(String(leerTemperatura()));
    

    //*************************************************************
    }else if(cmd.equals("GET_RAW")){
      leerBalanza(sensorConfig.masa_smpl_avg);
      rs485_send(String(reading_raw[0]) + "," + String(reading_raw[1]) + "," + String(reading_raw[2]) + "," + String(reading_raw[3]));
    

    //*************************************************************
    }else if(cmd.equals("SET_PROP_A1")){
      auxFloat = par.toFloat();
      sensorConfig.prop[0] = auxFloat;
      EEPROM.put(0, sensorConfig);
      send_ok();


    //*************************************************************  
    }else if(cmd.equals("SET_PROP_B1")){
      auxFloat = par.toFloat();
      sensorConfig.prop[1] = auxFloat;
      EEPROM.put(0, sensorConfig);
      send_ok();


    //*************************************************************  
    }else if(cmd.equals("SET_PROP_A2")){
      auxFloat = par.toFloat();
      sensorConfig.prop[2] = auxFloat;
      EEPROM.put(0, sensorConfig);
      send_ok();


    //*************************************************************  
    }else if(cmd.equals("SET_PROP_B2")){
      auxFloat = par.toFloat();
      sensorConfig.prop[3] = auxFloat;
      EEPROM.put(0, sensorConfig);
      send_ok();


    //*************************************************************  
    }else if(cmd.equals("SET_OFFSET_A1")){
      auxFloat = par.toFloat();
      sensorConfig.offset[0] = auxFloat;
      EEPROM.put(0, sensorConfig);
      send_ok();

    //*************************************************************
    }else if(cmd.equals("SET_OFFSET_B1")){
      auxFloat = par.toFloat();
      sensorConfig.offset[1] = auxFloat;
      EEPROM.put(0, sensorConfig);
      send_ok();

    //*************************************************************
    }else if(cmd.equals("SET_OFFSET_A2")){
      auxFloat = par.toFloat();
      sensorConfig.offset[2] = auxFloat;
      EEPROM.put(0, sensorConfig);
      send_ok();

    //*************************************************************
    }else if(cmd.equals("SET_OFFSET_B2")){
      auxFloat = par.toFloat();
      sensorConfig.offset[3] = auxFloat;
      EEPROM.put(0, sensorConfig);
      send_ok();

    //*************************************************************
    }else if(cmd.equals("TARE_ON")){
      rs485_send(" Wait...");
      sensorConfig.tara = -(calculo_masa(sensorConfig.masa_smpl_avg) * sensorConfig.cal_p + sensorConfig.cal_o);
      EEPROM.put(0, sensorConfig);
      send_ok();

      //*************************************************************
    }else if(cmd.equals("TARE_OFF")){
      sensorConfig.tara = 0;
      EEPROM.put(0, sensorConfig);
      send_ok();

      //*************************************************************
    }else if(cmd.equals("SET_SMPL_AVG")){
      auxInt = par.toInt();
      sensorConfig.masa_smpl_avg = auxInt;
      EEPROM.put(0, sensorConfig);
      send_ok();

      //*************************************************************
    }else if(cmd.equals("SET_PROP")){
      auxFloat = par.toFloat();
      sensorConfig.cal_p = auxFloat;
      EEPROM.put(0, sensorConfig);
      send_ok();

      //*************************************************************
    }else if(cmd.equals("SET_OFFSET")){
      auxFloat = par.toFloat();
      sensorConfig.cal_o = auxFloat;
      EEPROM.put(0, sensorConfig);
      send_ok();

      //*************************************************************
    }else if(cmd.equals("GET_SENS")){
      rs485_send(sensorsConnected());

      //*************************************************************
    }else if(cmd.equals("SET_TXD")){
      auxFloat = par.toFloat();
      sensorConfig.transmitDelay = auxFloat;
      EEPROM.put(0, sensorConfig);
      send_ok();

      //*************************************************************
    }
  
  }else if(id == 255){
    delay(random(0,1000));rs485_send(String(sensorConfig.rs485_id));
  }
}






//=================================================================================================
//  READ COM MESSAGES
//=================================================================================================
void checkComMessage() 
{
  // Check if there is data available to read from the serial port
 if (!Serial.available()) return ;
  delay(50);
  
  Serial.setTimeout(100);
  int cant_bytes_cmd=0;//max 63 bytes en un comando
  while (char(Serial.read())!='<' && Serial.available());//  leer el serial hasta encontrar un '<' que es el inicio de un comando
  if (!Serial.available()) return ;  //si lleo todo el buffer y no quedan bytes sin encontrar el < se sale
  
  //ledStatus(true);

  cant_bytes_cmd=1;
  String command="<";    
  bool fin_de_comando=false;
  while (Serial.available()&&cant_bytes_cmd<128&&!fin_de_comando)
  {
    byte inChar = Serial.read();
    if (inChar>=32 && inChar<=126)  command +=String(char(inChar));//do not include non text bytes 
    cant_bytes_cmd++;
    if (char(inChar)=='>') fin_de_comando=true;
  }
  if (!fin_de_comando) return;
  
    //String command = Serial.readStringUntil('\n'); // Read the incoming command until '>' (not included) character is found
    // Check if the command has the correct format
    if (command.startsWith("<") && (command.endsWith(">") || command.endsWith(">\r"))) {
      command = command.substring(1, command.indexOf('>')); // Remove the '<' & '>' characters
      
      // Extract the individual components from the command
      int id = command.substring(0, command.indexOf(',')).toInt(); // Extract the ID as an integer
      command = command.substring(command.indexOf(',') + 1); // Remove the ID and comma
      
      String cmd, par;
      
      // Check if the command has a parameter
      if (command.indexOf(',') != -1) {
        cmd = command.substring(0, command.indexOf(',')); // Extract the command
        par = command.substring(command.indexOf(',') + 1); // Extract the parameter
      } else {
        cmd = command; // The command doesn't have a parameter
      }
     // Convert the command to uppercase for case insensitivity
      cmd.toUpperCase();
      processCmd(id, cmd, par);
      
    }
  delay(500);
  //ledStatus(false);
}
