from pydantic import BaseModel, Field
from pymodbus.client import ModbusTcpClient
from typing import List, Dict, Any, Optional, Union
import logging

# Configurar logging
logger = logging.getLogger(__name__)

def validate_and_convert_modbus_params(HOST: str, PORT: Union[int, float, str], SLAVE_UNIT: Union[int, float, str]) -> tuple:
    """
    Valida y convierte los parámetros básicos de Modbus a los tipos correctos.
    
    Args:
        HOST: Dirección IP del dispositivo
        PORT: Puerto TCP (debe ser entero)
        SLAVE_UNIT: ID del dispositivo esclavo (debe ser entero)
        
    Returns:
        tuple: (HOST, PORT_int, SLAVE_UNIT_int) con tipos validados
        
    Raises:
        ValueError: Si los parámetros no son válidos
    """
    try:
        # Validar HOST
        if not isinstance(HOST, str) or not HOST.strip():
            raise ValueError(f"HOST debe ser una cadena no vacía, recibido: {type(HOST)} = {HOST}")
        
        # Convertir y validar PORT
        try:
            port_int = int(float(PORT))  # Convierte float a int primero
            if not (1 <= port_int <= 65535):
                raise ValueError(f"PORT debe estar entre 1 y 65535, recibido: {port_int}")
        except (ValueError, TypeError) as e:
            raise ValueError(f"PORT debe ser un número entero válido, recibido: {type(PORT)} = {PORT}") from e
        
        # Convertir y validar SLAVE_UNIT
        try:
            slave_int = int(float(SLAVE_UNIT))  # Convierte float a int primero
            if not (1 <= slave_int <= 247):
                raise ValueError(f"SLAVE_UNIT debe estar entre 1 y 247, recibido: {slave_int}")
        except (ValueError, TypeError) as e:
            raise ValueError(f"SLAVE_UNIT debe ser un número entero válido, recibido: {type(SLAVE_UNIT)} = {SLAVE_UNIT}") from e
        
        logger.debug(f"Parámetros validados: HOST={HOST}, PORT={port_int}, SLAVE_UNIT={slave_int}")
        return HOST.strip(), port_int, slave_int
        
    except Exception as e:
        logger.error(f"Error validando parámetros Modbus: {e}")
        raise

def validate_and_convert_addresses(addresses: Union[int, float, str, List], address_type: str = "coil") -> Union[int, List[int]]:
    """
    Valida y convierte direcciones de coils o registros a enteros.
    
    Args:
        addresses: Dirección(es) a validar
        address_type: Tipo de dirección ("coil" o "register")
        
    Returns:
        Dirección(es) convertida(s) a entero(s)
        
    Raises:
        ValueError: Si las direcciones no son válidas
    """
    try:
        if isinstance(addresses, (int, float, str)):
            # Una sola dirección
            try:
                addr_int = int(float(addresses))
                max_addr = 65535 if address_type == "register" else 65535
                if not (0 <= addr_int <= max_addr):
                    raise ValueError(f"{address_type.upper()} debe estar entre 0 y {max_addr}, recibido: {addr_int}")
                return addr_int
            except (ValueError, TypeError) as e:
                raise ValueError(f"{address_type.upper()} debe ser un número entero válido, recibido: {type(addresses)} = {addresses}") from e
        
        elif isinstance(addresses, list):
            # Múltiples direcciones
            converted_addresses = []
            for addr in addresses:
                try:
                    addr_int = int(float(addr))
                    max_addr = 65535 if address_type == "register" else 65535
                    if not (0 <= addr_int <= max_addr):
                        raise ValueError(f"{address_type.upper()} debe estar entre 0 y {max_addr}, recibido: {addr_int}")
                    converted_addresses.append(addr_int)
                except (ValueError, TypeError) as e:
                    raise ValueError(f"{address_type.upper()} debe ser un número entero válido, recibido: {type(addr)} = {addr}") from e
            
            return converted_addresses
        
        else:
            raise ValueError(f"{address_type.upper()} debe ser int, float, str o List, recibido: {type(addresses)}")
            
    except Exception as e:
        logger.error(f"Error validando direcciones {address_type}: {e}")
        raise

def validate_coil_states(coil_addresses: Union[int, List[int], Dict], state: Optional[bool] = None) -> tuple:
    """
    Valida y convierte los estados de coils.
    
    Args:
        coil_addresses: Direcciones de coils
        state: Estado para todas las coils (si aplica)
        
    Returns:
        tuple: (coil_addresses_converted, states_dict)
    """
    try:
        if isinstance(coil_addresses, (int, float, str)):
            # Una sola coil
            addr_int = validate_and_convert_addresses(coil_addresses, "coil")
            if state is None:
                raise ValueError("Debe especificar STATE para una sola coil")
            return addr_int, {addr_int: bool(state)}
        
        elif isinstance(coil_addresses, list):
            # Múltiples coils con el mismo estado
            addrs_int = validate_and_convert_addresses(coil_addresses, "coil")
            if state is None:
                raise ValueError("Debe especificar STATE para múltiples coils")
            return addrs_int, {addr: bool(state) for addr in addrs_int}
        
        elif isinstance(coil_addresses, dict):
            # Coils con estados específicos
            states_dict = {}
            for addr, coil_state in coil_addresses.items():
                addr_int = validate_and_convert_addresses(addr, "coil")
                states_dict[addr_int] = bool(coil_state)
            return list(states_dict.keys()), states_dict
        
        else:
            raise ValueError(f"COIL_ADDRESSES debe ser int, List[int] o Dict[int, bool], recibido: {type(coil_addresses)}")
            
    except Exception as e:
        logger.error(f"Error validando estados de coils: {e}")
        raise

def validate_register_values(addresses: Union[int, List, Dict], values: Union[int, float, str, List] = None) -> tuple:
    """
    Valida y convierte los valores de registros.
    
    Args:
        addresses: Direcciones de registros
        values: Valores para los registros (si aplica)
        
    Returns:
        tuple: (addresses_converted, values_dict)
    """
    try:
        if isinstance(addresses, (int, float, str)):
            # Un solo registro
            addr_int = validate_and_convert_addresses(addresses, "register")
            if values is None:
                raise ValueError("Debe especificar VALUES para un solo registro")
            
            # Convertir valor a int
            try:
                value_int = int(float(values))
                if not (0 <= value_int <= 65535):
                    raise ValueError(f"Valor de registro debe estar entre 0 y 65535, recibido: {value_int}")
            except (ValueError, TypeError) as e:
                raise ValueError(f"VALUES debe ser un número entero válido, recibido: {type(values)} = {values}") from e
            
            return addr_int, {addr_int: value_int}
        
        elif isinstance(addresses, list):
            # Múltiples registros con el mismo valor o valores específicos
            addrs_int = validate_and_convert_addresses(addresses, "register")
            
            if values is None:
                raise ValueError("Debe especificar VALUES para múltiples registros")
            
            if isinstance(values, (int, float, str)):
                # Mismo valor para todos
                try:
                    value_int = int(float(values))
                    if not (0 <= value_int <= 65535):
                        raise ValueError(f"Valor de registro debe estar entre 0 y 65535, recibido: {value_int}")
                except (ValueError, TypeError) as e:
                    raise ValueError(f"VALUES debe ser un número entero válido, recibido: {type(values)} = {values}") from e
                
                return addrs_int, {addr: value_int for addr in addrs_int}
            
            elif isinstance(values, list):
                # Valores específicos para cada registro
                if len(values) != len(addrs_int):
                    raise ValueError(f"El número de valores ({len(values)}) debe coincidir con el número de direcciones ({len(addrs_int)})")
                
                values_dict = {}
                for i, addr in enumerate(addrs_int):
                    try:
                        value_int = int(float(values[i]))
                        if not (0 <= value_int <= 65535):
                            raise ValueError(f"Valor de registro debe estar entre 0 y 65535, recibido: {value_int}")
                        values_dict[addr] = value_int
                    except (ValueError, TypeError) as e:
                        raise ValueError(f"VALUES[{i}] debe ser un número entero válido, recibido: {type(values[i])} = {values[i]}") from e
                
                return addrs_int, values_dict
            else:
                raise ValueError(f"VALUES debe ser int, float, str o List, recibido: {type(values)}")
        
        elif isinstance(addresses, dict):
            # Registros con valores específicos
            values_dict = {}
            for addr, value in addresses.items():
                addr_int = validate_and_convert_addresses(addr, "register")
                try:
                    value_int = int(float(value))
                    if not (0 <= value_int <= 65535):
                        raise ValueError(f"Valor de registro debe estar entre 0 y 65535, recibido: {value_int}")
                    values_dict[addr_int] = value_int
                except (ValueError, TypeError) as e:
                    raise ValueError(f"Valor para registro {addr} debe ser un número entero válido, recibido: {type(value)} = {value}") from e
            
            return list(values_dict.keys()), values_dict
        
        else:
            raise ValueError(f"ADDRESSES debe ser int, List o Dict, recibido: {type(addresses)}")
            
    except Exception as e:
        logger.error(f"Error validando valores de registros: {e}")
        raise

class ModbusWriteCoilInput(BaseModel):
    """
    Esquema para escribir una o múltiples coils en un dispositivo Modbus TCP.
    """
    HOST: str = Field(description="Dirección IP del dispositivo Modbus TCP (e.g., '192.168.1.10').")
    PORT: Union[int, float, str] = Field(description="Número de puerto de red de la conexión TCP (Típicamente es 502) - se convierte automáticamente a int")
    COIL_ADDRESSES: Union[int, float, str, List, Dict] = Field(
        description="Dirección(es) de coil(s) a escribir. Puede ser: int/float/str (una coil), List (múltiples coils con mismo estado), o Dict (coils con estados específicos)."
    )
    STATE: Optional[bool] = Field(default=None, description="Estado a escribir para todas las coils (solo si COIL_ADDRESSES es int o List[int])")
    SLAVE_UNIT: Union[int, float, str] = Field(description="Dirección ID del dispositivo esclavo en la red (e.g., 3) - se convierte automáticamente a int")

class ModbusReadCoilInput(BaseModel):
    """
    Esquema para leer el estado de una o múltiples coils en un dispositivo Modbus TCP.
    """
    HOST: str = Field(description="Dirección IP del dispositivo Modbus TCP (e.g., '192.168.1.10').")
    PORT: Union[int, float, str] = Field(description="Número de puerto de red de la conexión TCP (Típicamente es 502) - se convierte automáticamente a int")
    COIL_ADDRESSES: Union[int, float, str, List] = Field(
        description="Dirección(es) de coil(s) a leer. Puede ser: int/float/str (una coil) o List (múltiples coils específicas)."
    )
    SLAVE_UNIT: Union[int, float, str] = Field(description="Dirección ID del dispositivo esclavo en la red (e.g., 3) - se convierte automáticamente a int")

class ModbusReadHoldingRegisters(BaseModel):
    """
    Esquema para leer los valores de los registros de holding en un dispositivo Modbus TCP.
    """
    HOST: str = Field(description="Dirección IP del dispositivo Modbus TCP (e.g., '192.168.1.10').")
    PORT: Union[int, float, str] = Field(description="Número de puerto de red de la conexión TCP (Típicamente es 502) - se convierte automáticamente a int")
    ADDRESSES: Union[int, float, str, List] = Field(
        description="Dirección(es) de registro(s) de holding a leer. Puede ser: int/float/str (un registro) o List (múltiples registros específicos)."
    )
    SLAVE_UNIT: Union[int, float, str] = Field(description="Dirección ID del dispositivo esclavo en la red (e.g., 3) - se convierte automáticamente a int")

class ModbusReadInputRegisters(BaseModel):
    """
    Esquema para leer los valores de los registros de entrada en un dispositivo Modbus TCP.
    """
    HOST: str = Field(description="Dirección IP del dispositivo Modbus TCP (e.g., '192.168.1.10').")
    PORT: Union[int, float, str] = Field(description="Número de puerto de red de la conexión TCP (Típicamente es 502) - se convierte automáticamente a int")
    ADDRESSES: Union[int, float, str, List] = Field(
        description="Dirección(es) de registro(s) de entrada a leer. Puede ser: int/float/str (un registro) o List (múltiples registros específicos)."
    )
    SLAVE_UNIT: Union[int, float, str] = Field(description="Dirección ID del dispositivo esclavo en la red (e.g., 3) - se convierte automáticamente a int")

class ModbusWriteRegisterInput(BaseModel):
    """
    Esquema para escribir valores en uno o múltiples registros de holding en un dispositivo Modbus TCP.
    """
    HOST: str = Field(description="Dirección IP del dispositivo Modbus TCP (e.g., '192.168.1.10').")
    PORT: Union[int, float, str] = Field(description="Número de puerto de red de la conexión TCP (Típicamente es 502) - se convierte automáticamente a int")
    ADDRESSES: Union[int, float, str, List, Dict] = Field(
        description="Dirección(es) de registro(s) de holding a escribir. Puede ser: int/float/str (un registro), List (múltiples registros con mismo valor), o Dict (registros con valores específicos)."
    )
    VALUES: Union[int, float, str, List] = Field(
        description="Valor(es) a escribir en los registros. Puede ser: int/float/str (un valor), List (múltiples valores). Solo se usa si ADDRESSES es int o List."
    )
    SLAVE_UNIT: Union[int, float, str] = Field(description="Dirección ID del dispositivo esclavo en la red (e.g., 3) - se convierte automáticamente a int")

class ModbusTool:
    """
    Herramienta para comunicación con dispositivos Modbus TCP.
    Permite leer y escribir coils, registros de holding y registros de entrada.
    Soporta operaciones múltiples en una sola llamada.
    """
    
    def __init__(self):
        """Inicializa la herramienta Modbus."""
        pass
    
    def write_modbus_coil(self, HOST: str, PORT: Union[int, float, str], COIL_ADDRESSES: Union[int, float, str, List, Dict], SLAVE_UNIT: Union[int, float, str], STATE: Optional[bool] = None) -> Dict[str, Any]:
        """
        Utiliza Modbus TCP para establecer una o múltiples salidas digitales (Coils) a ON (True) o OFF (False).
        
        Args:
            HOST: Dirección IP del dispositivo Modbus TCP
            PORT: Número de puerto de red (típicamente 502) - se convierte automáticamente a int
            COIL_ADDRESSES: Puede ser:
                - int/float/str: Una sola coil
                - List: Múltiples coils con el mismo estado
                - Dict: Coils con estados específicos
            SLAVE_UNIT: Dirección ID del dispositivo esclavo - se convierte automáticamente a int
            STATE: Estado a escribir (solo si COIL_ADDRESSES es int o List[int])
            
        Returns:
            Dict con el resultado de la operación
        """
        try:
            # Validar y convertir parámetros básicos
            host_validated, port_int, slave_int = validate_and_convert_modbus_params(HOST, PORT, SLAVE_UNIT)
            
            # Validar y convertir direcciones y estados de coils
            coil_addresses_converted, states_dict = validate_coil_states(COIL_ADDRESSES, STATE)
            
            client = ModbusTcpClient(host_validated, port=port_int)
            if not client.connect():
                return {
                    "success": False,
                    "error": "No se pudo conectar con el cliente Modbus",
                    "details": f"Verifique la IP {host_validated} y puerto {port_int}"
                }

            # Ejecutar operaciones de escritura
            results = []
            errors = []
            
            for coil_addr, coil_state in states_dict.items():
                try:
                    result = client.write_coil(coil_addr, coil_state, device_id=slave_int)
                    if result.isError():
                        errors.append(f"Coil {coil_addr}: {result}")
                    else:
                        results.append({
                            "coil_address": coil_addr,
                            "state": coil_state,
                            "status": "success"
                        })
                except Exception as e:
                    errors.append(f"Coil {coil_addr}: {str(e)}")

            client.close()
            
            if errors:
                return {
                    "success": False,
                    "error": f"Errores en escritura de coils: {len(errors)} de {len(states_dict)}",
                    "details": {
                        "successful_operations": results,
                        "errors": errors,
                        "slave_unit": slave_int
                    }
                }
            else:
                return {
                    "success": True,
                    "message": f"Todas las coils escritas exitosamente ({len(results)} operaciones)",
                    "details": {
                        "operations": results,
                        "slave_unit": slave_int
                    }
                }

        except Exception as e:
            return {
                "success": False,
                "error": f"Excepción durante escritura de coils: {str(e)}",
                "details": f"HOST: {HOST}, PORT: {PORT}"
            }

    def read_modbus_coil(self, HOST: str, PORT: Union[int, float, str], COIL_ADDRESSES: Union[int, float, str, List], SLAVE_UNIT: Union[int, float, str]) -> Dict[str, Any]:
        """
        Lee el estado de una o múltiples coils en un dispositivo Modbus TCP.
        
        Args:
            HOST: Dirección IP del dispositivo Modbus TCP
            PORT: Número de puerto de red (típicamente 502) - se convierte automáticamente a int
            COIL_ADDRESSES: Puede ser:
                - int/float/str: Una sola coil
                - List: Múltiples coils específicas
            SLAVE_UNIT: Dirección ID del dispositivo esclavo - se convierte automáticamente a int
            
        Returns:
            Dict con el resultado de la operación y los valores leídos
        """
        try:
            # Validar y convertir parámetros básicos
            host_validated, port_int, slave_int = validate_and_convert_modbus_params(HOST, PORT, SLAVE_UNIT)
            
            # Validar y convertir direcciones de coils
            coil_addresses_converted = validate_and_convert_addresses(COIL_ADDRESSES, "coil")
            
            client = ModbusTcpClient(host_validated, port=port_int)
            if not client.connect():
                return {
                    "success": False,
                    "error": "No se pudo conectar con el cliente Modbus",
                    "details": f"Verifique la IP {host_validated} y puerto {port_int}"
                }

            # Si hay múltiples coils, leer en lotes para eficiencia
            all_results = []
            errors = []
            
            if isinstance(coil_addresses_converted, int):
                # Una sola coil
                coil_addr = coil_addresses_converted
                try:
                    result = client.read_coils(coil_addr, count=1, device_id=slave_int)
                    if result.isError():
                        errors.append(f"Coil {coil_addr}: {result}")
                    else:
                        all_results.append({
                            "coil_address": coil_addr,
                            "state": result.bits[0],
                            "status": "success"
                        })
                except Exception as e:
                    errors.append(f"Coil {coil_addr}: {str(e)}")
            else:
                # Múltiples coils - leer en lotes contiguos cuando sea posible
                coil_addresses_converted.sort()
                i = 0
                while i < len(coil_addresses_converted):
                    start_addr = coil_addresses_converted[i]
                    # Encontrar el siguiente lote contiguo
                    j = i
                    while j < len(coil_addresses_converted) and coil_addresses_converted[j] == start_addr + (j - i):
                        j += 1
                    
                    # Leer el lote contiguo
                    count = j - i
                    try:
                        result = client.read_coils(start_addr, count=count, device_id=slave_int)
                        if result.isError():
                            # Si falla el lote, leer individualmente
                            for k in range(i, j):
                                try:
                                    individual_result = client.read_coils(coil_addresses_converted[k], count=1, device_id=slave_int)
                                    if not individual_result.isError():
                                        all_results.append({
                                            "coil_address": coil_addresses_converted[k],
                                            "state": individual_result.bits[0],
                                            "status": "success"
                                        })
                                    else:
                                        errors.append(f"Coil {coil_addresses_converted[k]}: {individual_result}")
                                except Exception as e:
                                    errors.append(f"Coil {coil_addresses_converted[k]}: {str(e)}")
                        else:
                            # Procesar resultado del lote
                            for k in range(i, j):
                                all_results.append({
                                    "coil_address": coil_addresses_converted[k],
                                    "state": result.bits[k - i],
                                    "status": "success"
                                })
                    except Exception as e:
                        # Si falla el lote, leer individualmente
                        for k in range(i, j):
                            try:
                                individual_result = client.read_coils(coil_addresses_converted[k], count=1, device_id=slave_int)
                                if not individual_result.isError():
                                    all_results.append({
                                        "coil_address": coil_addresses_converted[k],
                                        "state": individual_result.bits[0],
                                        "status": "success"
                                    })
                                else:
                                    errors.append(f"Coil {coil_addresses_converted[k]}: {individual_result}")
                            except Exception as e2:
                                errors.append(f"Coil {coil_addresses_converted[k]}: {str(e2)}")
                    
                    i = j

            client.close()
            
            if errors:
                return {
                    "success": False,
                    "error": f"Errores en lectura de coils: {len(errors)} de {len(coil_addresses_converted) if isinstance(coil_addresses_converted, list) else 1}",
                    "details": {
                        "successful_reads": all_results,
                        "errors": errors,
                        "slave_unit": slave_int
                    }
                }
            else:
                return {
                    "success": True,
                    "message": f"Todas las coils leídas exitosamente ({len(all_results)} coils)",
                    "details": {
                        "coil_states": all_results,
                        "slave_unit": slave_int
                    }
                }

        except Exception as e:
            return {
                "success": False,
                "error": f"Excepción durante lectura de coils: {str(e)}",
                "details": f"HOST: {HOST}, PORT: {PORT}"
            }

    def read_modbus_holding_registers(self, HOST: str, PORT: Union[int, float, str], ADDRESSES: Union[int, float, str, List], SLAVE_UNIT: Union[int, float, str]) -> Dict[str, Any]:
        """
        Lee los valores de uno o múltiples registros de holding en un dispositivo Modbus TCP.
        
        Args:
            HOST: Dirección IP del dispositivo Modbus TCP
            PORT: Número de puerto de red (típicamente 502) - se convierte automáticamente a int
            ADDRESSES: Puede ser:
                - int/float/str: Un solo registro
                - List: Múltiples registros específicos
            SLAVE_UNIT: Dirección ID del dispositivo esclavo - se convierte automáticamente a int
            
        Returns:
            Dict con el resultado de la operación y los valores leídos
        """
        try:
            # Validar y convertir parámetros básicos
            host_validated, port_int, slave_int = validate_and_convert_modbus_params(HOST, PORT, SLAVE_UNIT)
            
            # Validar y convertir direcciones de registros
            addresses_converted = validate_and_convert_addresses(ADDRESSES, "register")
            
            client = ModbusTcpClient(host_validated, port=port_int)
            if not client.connect():
                return {
                    "success": False,
                    "error": "No se pudo conectar con el cliente Modbus",
                    "details": f"Verifique la IP {host_validated} y puerto {port_int}"
                }

            # Leer registros en lotes contiguos cuando sea posible
            all_results = []
            errors = []
            
            if isinstance(addresses_converted, int):
                # Un solo registro
                addr = addresses_converted
                try:
                    result = client.read_holding_registers(address=addr, count=1, device_id=slave_int)
                    if result.isError():
                        errors.append(f"Registro {addr}: {result}")
                    else:
                        all_results.append({
                            "register_address": addr,
                            "value": result.registers[0],
                            "status": "success"
                        })
                except Exception as e:
                    errors.append(f"Registro {addr}: {str(e)}")
            else:
                # Múltiples registros - leer en lotes contiguos cuando sea posible
                addresses_converted.sort()
                i = 0
                while i < len(addresses_converted):
                    start_addr = addresses_converted[i]
                    # Encontrar el siguiente lote contiguo
                    j = i
                    while j < len(addresses_converted) and addresses_converted[j] == start_addr + (j - i):
                        j += 1
                    
                    # Leer el lote contiguo
                    count = j - i
                    try:
                        result = client.read_holding_registers(address=start_addr, count=count, device_id=slave_int)
                        if result.isError():
                            # Si falla el lote, leer individualmente
                            for k in range(i, j):
                                try:
                                    individual_result = client.read_holding_registers(address=addresses_converted[k], count=1, device_id=slave_int)
                                    if not individual_result.isError():
                                        all_results.append({
                                            "register_address": addresses_converted[k],
                                            "value": individual_result.registers[0],
                                            "status": "success"
                                        })
                                    else:
                                        errors.append(f"Registro {addresses_converted[k]}: {individual_result}")
                                except Exception as e:
                                    errors.append(f"Registro {addresses_converted[k]}: {str(e)}")
                        else:
                            # Procesar resultado del lote
                            for k in range(i, j):
                                all_results.append({
                                    "register_address": addresses_converted[k],
                                    "value": result.registers[k - i],
                                    "status": "success"
                                })
                    except Exception as e:
                        # Si falla el lote, leer individualmente
                        for k in range(i, j):
                            try:
                                individual_result = client.read_holding_registers(address=addresses_converted[k], count=1, device_id=slave_int)
                                if not individual_result.isError():
                                    all_results.append({
                                        "register_address": addresses_converted[k],
                                        "value": individual_result.registers[0],
                                        "status": "success"
                                    })
                                else:
                                    errors.append(f"Registro {addresses_converted[k]}: {individual_result}")
                            except Exception as e2:
                                errors.append(f"Registro {addresses_converted[k]}: {str(e2)}")
                    
                    i = j

            client.close()
            
            if errors:
                return {
                    "success": False,
                    "error": f"Errores en lectura de registros de holding: {len(errors)} de {len(addresses_converted) if isinstance(addresses_converted, list) else 1}",
                    "details": {
                        "successful_reads": all_results,
                        "errors": errors,
                        "slave_unit": slave_int
                    }
                }
            else:
                return {
                    "success": True,
                    "message": f"Todos los registros de holding leídos exitosamente ({len(all_results)} registros)",
                    "details": {
                        "register_values": all_results,
                        "slave_unit": slave_int
                    }
                }

        except Exception as e:
            return {
                "success": False,
                "error": f"Excepción durante lectura de registros de holding: {str(e)}",
                "details": f"HOST: {HOST}, PORT: {PORT}"
            }

    def read_modbus_input_registers(self, HOST: str, PORT: Union[int, float, str], ADDRESSES: Union[int, float, str, List], SLAVE_UNIT: Union[int, float, str]) -> Dict[str, Any]:
        """
        Lee los valores de uno o múltiples registros de entrada en un dispositivo Modbus TCP.
        
        Args:
            HOST: Dirección IP del dispositivo Modbus TCP
            PORT: Número de puerto de red (típicamente 502) - se convierte automáticamente a int
            ADDRESSES: Puede ser:
                - int/float/str: Un solo registro
                - List: Múltiples registros específicos
            SLAVE_UNIT: Dirección ID del dispositivo esclavo - se convierte automáticamente a int
            
        Returns:
            Dict con el resultado de la operación y los valores leídos
        """
        try:
            # Validar y convertir parámetros básicos
            host_validated, port_int, slave_int = validate_and_convert_modbus_params(HOST, PORT, SLAVE_UNIT)
            
            # Validar y convertir direcciones de registros
            addresses_converted = validate_and_convert_addresses(ADDRESSES, "register")
            
            client = ModbusTcpClient(host_validated, port=port_int)
            if not client.connect():
                return {
                    "success": False,
                    "error": "No se pudo conectar con el cliente Modbus",
                    "details": f"Verifique la IP {host_validated} y puerto {port_int}"
                }

            # Leer registros en lotes contiguos cuando sea posible
            all_results = []
            errors = []
            
            if isinstance(addresses_converted, int):
                # Un solo registro
                addr = addresses_converted
                try:
                    result = client.read_input_registers(address=addr, count=1, device_id=slave_int)
                    if result.isError():
                        errors.append(f"Registro {addr}: {result}")
                    else:
                        all_results.append({
                            "register_address": addr,
                            "value": result.registers[0],
                            "status": "success"
                        })
                except Exception as e:
                    errors.append(f"Registro {addr}: {str(e)}")
            else:
                # Múltiples registros - leer en lotes contiguos cuando sea posible
                addresses_converted.sort()
                i = 0
                while i < len(addresses_converted):
                    start_addr = addresses_converted[i]
                    # Encontrar el siguiente lote contiguo
                    j = i
                    while j < len(addresses_converted) and addresses_converted[j] == start_addr + (j - i):
                        j += 1
                    
                    # Leer el lote contiguo
                    count = j - i
                    try:
                        result = client.read_input_registers(address=start_addr, count=count, device_id=slave_int)
                        if result.isError():
                            # Si falla el lote, leer individualmente
                            for k in range(i, j):
                                try:
                                    individual_result = client.read_input_registers(address=addresses_converted[k], count=1, device_id=slave_int)
                                    if not individual_result.isError():
                                        all_results.append({
                                            "register_address": addresses_converted[k],
                                            "value": individual_result.registers[0],
                                            "status": "success"
                                        })
                                    else:
                                        errors.append(f"Registro {addresses_converted[k]}: {individual_result}")
                                except Exception as e:
                                    errors.append(f"Registro {addresses_converted[k]}: {str(e)}")
                        else:
                            # Procesar resultado del lote
                            for k in range(i, j):
                                all_results.append({
                                    "register_address": addresses_converted[k],
                                    "value": result.registers[k - i],
                                    "status": "success"
                                })
                    except Exception as e:
                        # Si falla el lote, leer individualmente
                        for k in range(i, j):
                            try:
                                individual_result = client.read_input_registers(address=addresses_converted[k], count=1, device_id=slave_int)
                                if not individual_result.isError():
                                    all_results.append({
                                        "register_address": addresses_converted[k],
                                        "value": individual_result.registers[0],
                                        "status": "success"
                                    })
                                else:
                                    errors.append(f"Registro {addresses_converted[k]}: {individual_result}")
                            except Exception as e2:
                                errors.append(f"Registro {addresses_converted[k]}: {str(e2)}")
                    
                    i = j

            client.close()
            
            if errors:
                return {
                    "success": False,
                    "error": f"Errores en lectura de registros de entrada: {len(errors)} de {len(addresses_converted) if isinstance(addresses_converted, list) else 1}",
                    "details": {
                        "successful_reads": all_results,
                        "errors": errors,
                        "slave_unit": slave_int
                    }
                }
            else:
                return {
                    "success": True,
                    "message": f"Todos los registros de entrada leídos exitosamente ({len(all_results)} registros)",
                    "details": {
                        "register_values": all_results,
                        "slave_unit": slave_int
                    }
                }

        except Exception as e:
            return {
                "success": False,
                "error": f"Excepción durante lectura de registros de entrada: {str(e)}",
                "details": f"HOST: {HOST}, PORT: {PORT}"
            }

    def write_modbus_register(self, HOST: str, PORT: Union[int, float, str], ADDRESSES: Union[int, float, str, List, Dict], SLAVE_UNIT: Union[int, float, str], VALUES: Union[int, float, str, List] = None) -> Dict[str, Any]:
        """
        Utiliza Modbus TCP para escribir valores en uno o múltiples registros de holding.
        
        Args:
            HOST: Dirección IP del dispositivo Modbus TCP
            PORT: Número de puerto de red (típicamente 502) - se convierte automáticamente a int
            ADDRESSES: Puede ser:
                - int/float/str: Un solo registro
                - List: Múltiples registros con el mismo valor o valores específicos
                - Dict: Registros con valores específicos
            SLAVE_UNIT: Dirección ID del dispositivo esclavo - se convierte automáticamente a int
            VALUES: Valor(es) a escribir (solo si ADDRESSES es int o List)
            
        Returns:
            Dict con el resultado de la operación
        """
        try:
            # Validar y convertir parámetros básicos
            host_validated, port_int, slave_int = validate_and_convert_modbus_params(HOST, PORT, SLAVE_UNIT)
            
            # Validar y convertir direcciones y valores de registros
            addresses_converted, values_dict = validate_register_values(ADDRESSES, VALUES)
            
            client = ModbusTcpClient(host_validated, port=port_int)
            if not client.connect():
                return {
                    "success": False,
                    "error": "No se pudo conectar con el cliente Modbus",
                    "details": f"Verifique la IP {host_validated} y puerto {port_int}"
                }

            # Ejecutar operaciones de escritura
            results = []
            errors = []
            
            for addr, value in values_dict.items():
                try:
                    result = client.write_register(addr, value, device_id=slave_int)
                    if result.isError():
                        errors.append(f"Registro {addr}: {result}")
                    else:
                        results.append({
                            "register_address": addr,
                            "value": value,
                            "status": "success"
                        })
                except Exception as e:
                    errors.append(f"Registro {addr}: {str(e)}")

            client.close()
            
            if errors:
                return {
                    "success": False,
                    "error": f"Errores en escritura de registros: {len(errors)} de {len(values_dict)}",
                    "details": {
                        "successful_operations": results,
                        "errors": errors,
                        "slave_unit": slave_int
                    }
                }
            else:
                return {
                    "success": True,
                    "message": f"Todos los registros escritos exitosamente ({len(results)} operaciones)",
                    "details": {
                        "operations": results,
                        "slave_unit": slave_int
                    }
                }

        except Exception as e:
            return {
                "success": False,
                "error": f"Excepción durante escritura de registros: {str(e)}",
                "details": f"HOST: {HOST}, PORT: {PORT}"
            }

    def get_modbus_tools_list(self) -> List:
        """
        Retorna la lista de herramientas Modbus disponibles para uso con LLM.
        
        Returns:
            Lista de funciones Modbus para herramientas de LLM
        """
        return [
            self.write_modbus_coil,
            self.read_modbus_coil,
            self.write_modbus_register,
            self.read_modbus_holding_registers,
            self.read_modbus_input_registers
        ]