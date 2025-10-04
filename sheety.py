import requests
from typing import Dict, List, Optional


class SheetyClient:
    """
    Cliente para interactuar con la API de Sheety.
    
    Sheety permite conectar Google Sheets con APIs REST para crear, leer, 
    actualizar y eliminar datos de hojas de cálculo.
    
    Attributes:
        name (str): Nombre de la hoja/tabla en Sheety
        url (str): URL base de la API de Sheety
        keys (List[str]): Lista de claves válidas para filtrar los datos
        headers (Dict[str, str]): Headers HTTP para las requests
    """
    
    def __init__(self, name: str, url: str, keys: List[str], auth_token: Optional[str] = None):
        """
        Inicializa el cliente de Sheety.
        
        Args:
            name (str): Nombre de la hoja/tabla en Sheety
            url (str): URL completa de la API de Sheety (ej: https://api.sheety.co/tu_id/tu_proyecto/tu_hoja)
            keys (List[str]): Lista de nombres de columnas válidas para filtrar
            auth_token (Optional[str]): Token de autenticación si la API lo requiere
            
        Example:
            client = SheetyClient(
                name="usuarios",
                url="https://api.sheety.co/abc123/mi_proyecto/usuarios",
                keys=["nombre", "email", "edad"],
                auth_token="Bearer tu_token_aqui"
            )
        """
        self.name = name
        self.url = url
        self.keys = keys
        self.headers = {
            'Content-Type': 'application/json'
        }
        
        if auth_token:
            self.headers['Authorization'] = auth_token

    def post(self, data: Dict) -> bool:
        """
        Envía datos a Sheety mediante POST request.
        
        Filtra los datos de entrada usando las claves válidas definidas
        y los envía a la API de Sheety en el formato requerido.
        
        Args:
            data (Dict): Diccionario con los datos a enviar. Solo se enviarán
                        las claves que estén en self.keys
                        
        Returns:
            bool: True si el POST fue exitoso (status 200-299), False en caso contrario
            
        Raises:
            requests.exceptions.RequestException: Si hay problemas de conectividad
            
        Example:
            success = client.post({
                "nombre": "Juan Pérez",
                "email": "juan@example.com",
                "edad": 30,
                "dato_extra": "ignorado"  # Este campo será ignorado si no está en keys
            })
        """
        try:
            raw = {}
            for key in self.keys:
                if key in data:
                    raw[key] = data[key] if key in data else ""
            
            body = {
                self.name: raw
            }
            
            response = requests.post(
                self.url,
                json=body,
                headers=self.headers,
                timeout=30
            )
            
            response.raise_for_status()
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"Error al realizar POST a Sheety: {e}")
            return False
        except Exception as e:
            print(f"Error inesperado: {e}")
            return False


