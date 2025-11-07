#Estandarizando el desarrollo de agentes IA para CONAUTI :

Esta plantilla tiene como base:

(estructura de archivos + integración de modelo + prompt_template)


    #Plantilla Desarrollado en base a la primera version de Hector repliker.

    Se busca :
        agilizar el proceso de desarrollo de los agentes IA en general (watts)


-----------------------------------------------------------
#para poder activar el entorno virtual en shell :

python -m venv venv
venv\Scripts\Activate
pip install -r requirements.txt

#para comprobar la conexion con el mongo DB atlas
python config.py

#activar api de forma local
python -m api.api

#para ejecutar main.py de edgemant ------ multiagente
python -m multiagent.main

-------------------------------------------------------------

Objetivo de este modelo.

Este proyecto ahora es un multiagente usando langgraph.

Primero hay un LLM que razona para saber a que agente especializado acudir segun necesidades del usuario.

Esta version contiene entrada de imagen y texto usando gemini-2.5-flash para dar información de electroválvulas o diagnóstico de la imagen de una, tambien puede hacer RAG.
