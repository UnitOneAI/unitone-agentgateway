use std::cell::RefCell;
use std::collections::HashMap;

// Tool registry: server_name -> { tool_name -> fingerprint }
thread_local! {
    static TOOL_REGISTRY: RefCell<HashMap<String, HashMap<String, String>>> =
        RefCell::new(HashMap::new());
}

pub fn get_tool_registry<F, R>(f: F) -> R
where
    F: FnOnce(&HashMap<String, HashMap<String, String>>) -> R,
{
    TOOL_REGISTRY.with(|reg| f(&reg.borrow()))
}

pub fn update_tool_registry<F>(f: F)
where
    F: FnOnce(&mut HashMap<String, HashMap<String, String>>),
{
    TOOL_REGISTRY.with(|reg| f(&mut reg.borrow_mut()))
}
