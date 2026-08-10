import sys
import logging
from src.storage import (
    ChatStorage,
    CrmDatabase,
    import_leads_from_directory,
    list_lead_files,
)
from src.ui import TerminalUI
from src.settings import ManageSettings
import src.config as config
from src.utils.exceptions import ConfigError, CrmDbError, LeadLoadError


logger = logging.getLogger(__name__)


def start_chat_session(
    ui: TerminalUI,
    storage: ChatStorage,
    loaded_filename: str = None
) -> bool:
    """Returns: True to return to menu, False to exit"""
    from src.app import (
        ChatSession, ChatLoop,
        ModelInitializer, RAGInitializer, ChatHistoryLoader
    )
    
    model_init = ModelInitializer(ui)
    rag_init = RAGInitializer(ui)
    history_loader = ChatHistoryLoader(ui, storage)
    
    # Load model
    model_handler = model_init.load(config.MODEL_NAME)
    if not model_handler:
        return True  # Return to menu
    
    # Load RAG
    rag_manager = rag_init.load()
    
    # Create session
    session = ChatSession(model_handler, rag_manager)
    
    # Load history if requested
    if loaded_filename:
        history_loader.load(loaded_filename, session.context_manager)
    
    # Run chat loop
    chat_loop = ChatLoop(session, ui, storage, loaded_filename)
    return chat_loop.run()


def main():
    """Main entry point"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger.info("Terminal CRM starting...")
    
    # Load config
    try:
        config.load_config()
    except ConfigError as e:
        print(f"Configuration error: {e}")
        sys.exit(1)
    
    # Create UI and storage
    ui = TerminalUI()
    storage = ChatStorage()
    crm_db = CrmDatabase()
    
    # Main menu 
    while True:
        choice = ui.show_main_menu()
        
        if choice == "Exit":
            sys.exit(0)
        
        elif choice == "Add Leads":
            try:
                filenames = [path.name for path in list_lead_files()]
                if not ui.confirm_lead_import(filenames):
                    continue
                summary = import_leads_from_directory(crm_db)
                ui.show_lead_import_summary(summary)
            except (CrmDbError, LeadLoadError) as e:
                ui.display_error(str(e))

        elif choice == "Dial":
            from src.ui.terminal import ansi_clear
            ansi_clear()
            with ui.status("Loading dialer..."):
                # Import dial_loop directly to avoid loading the model stack
                from src.app.dial_loop import DialLoop
                dial_loop = DialLoop(ui, crm_db)
            dial_loop.run()
        
        elif choice == "Settings":
            ManageSettings(ui.console).run()
            config.load_config()
        
        elif choice == "Load Chat":
            chats = storage.list_chats()
            selected = ui.show_chat_selection(chats)
            if selected:
                should_return = start_chat_session(ui, storage, selected)
                if not should_return:
                    sys.exit(0)
        
        elif choice == "New Chat":
            should_return = start_chat_session(ui, storage)
            if not should_return:
                sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        print(f"\nFatal error: {e}")
        sys.exit(1)