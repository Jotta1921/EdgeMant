from langgraph.graph import StateGraph
from .agents.agent_main import AgentMain
from multiagent.agents.agent_electrovalvula import AgentElectrovalvula
from multiagent.agents.agent_modbus import AgentModbus
from config import MONGO_URI, GEMINI_API_KEY
from multiagent.memory.mongodb_memory import MongoMemory

# Usa GEMINI_API_KEY directamente desde config.py
if not GEMINI_API_KEY:
    raise RuntimeError("Debes definir GEMINI_API_KEY en config.py con tu clave de Gemini 2.5 Flash.")


# Instancia memoria MongoDB
memory_db = MongoMemory(MONGO_URI)

# Instancia agentes con acceso a memoria
main_agent = AgentMain(GEMINI_API_KEY, memory_db)
electrovalvula_agent = AgentElectrovalvula(GEMINI_API_KEY, memory_db)
modbus_agent = AgentModbus(GEMINI_API_KEY, memory_db)

# Grafo LangGraph
graph = StateGraph(dict)

def nodo_main(state, **kwargs):
    query = state["query"]
    user_id = state.get("user_id", "anon")
    history = memory_db.get_conversation(user_id)
    memory_db.save_message(user_id, "user", query)
    next_agent = main_agent.decide_agent(query, history=history, user_id=user_id)
    if next_agent == "electrovalvula" or next_agent == "modbus":
        return {"next": next_agent, "state": state}
    else:
        respuesta = main_agent.run(query, history=history, user_id=user_id)
        memory_db.save_message(user_id, "agent", respuesta)
        return {"result": {
            "response": respuesta,
            "agent_used": "main",
            "rag_activated": False
        }}

def nodo_electrovalvula(state, **kwargs):
    query = state["query"] if "query" in state else state.get("state", {}).get("query", "")
    user_id = state.get("user_id", "anon")
    history = memory_db.get_conversation(user_id)
    
    # Ejecutar agente y obtener información sobre si usó RAG
    result = electrovalvula_agent.run_with_info(query, history=history, user_id=user_id)
    
    # Si el agente devuelve información extendida, usarla
    if isinstance(result, dict):
        respuesta = result.get("response", "")
        rag_used = result.get("rag_activated", False)
    else:
        # Compatibilidad con formato anterior
        respuesta = result
        rag_used = None
    
    memory_db.save_message(user_id, "agent", respuesta)
    return {"result": {
        "response": respuesta,
        "agent_used": "electrovalvula",
        "rag_activated": rag_used
    }}

def nodo_modbus(state, **kwargs):
    query = state["query"] if "query" in state else state.get("state", {}).get("query", "")
    user_id = state.get("user_id", "anon")
    history = memory_db.get_conversation(user_id)
    
    # Ejecutar agente Modbus
    respuesta = modbus_agent.run(query, history=history, user_id=user_id)
    
    memory_db.save_message(user_id, "agent", respuesta)
    return {"result": {
        "response": respuesta,
        "agent_used": "modbus",
        "rag_activated": False
    }}

graph.add_node("main", nodo_main)
graph.add_node("electrovalvula", nodo_electrovalvula)
graph.add_node("modbus", nodo_modbus)
graph.set_entry_point("main")

# Decisión de ruteo según salida del nodo principal
def router_path(state, **kwargs):
    # Solo rutear si el nodo anterior devolvió {'next', 'state'}
    if isinstance(state, dict) and "next" in state and "state" in state:
        return state["next"], state["state"]
    # Si no, terminar el flujo (el nodo anterior devolvió {'result'})
    return "__end__", state

graph.add_conditional_edges("main", router_path)

executable_graph = graph.compile()

def process_message_multiagent(state: dict):
    result = executable_graph.invoke(state)
    final_result = result.get("result", "Sin respuesta")
    
    # Si el resultado es un dict con información extendida, devolverlo tal como está
    if isinstance(final_result, dict):
        return final_result
    else:
        # Compatibilidad con formato anterior (solo string)
        return {
            "response": final_result,
            "agent_used": "unknown",
            "rag_activated": None
        }

def main_cli():
    print("¡Bienvenido al Multiagente Edgemant!")
    print("Escribe 'salir' para terminar la conversación")
    user_id = input("Ingrese su ID de usuario: ")
    while True:
        user_input = input("\nTú: ")
        if user_input.lower() in ["salir", "exit", "quit"]:
            break
        state = {"query": user_input, "user_id": user_id}
        answer = process_message_multiagent(state)
        #print(f"\nAgente: {answer}")
        print("Agente:")
        print(f"{answer['response']}")
        print("*")
        print("*")
        print("*")
        print(f"agent_used:{answer['agent_used']}")

if __name__ == "__main__":
    main_cli()