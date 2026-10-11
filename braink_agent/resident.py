"""Declared integration correction over pinned native resident code.

Exact identifiers replace legacy substring matching at this manager boundary.
The vendored source remains unchanged and hash-verifiable.
"""
def exact_store_class(native):
    class ExactCapabilityStore(native.EnterpriseStore):
        def _dispatch(self, state, product, operation, payload):
            def capabilities(value):
                if not isinstance(value, list) or not value or any(not isinstance(x, str) or not x.strip() or x != x.strip() for x in value):
                    raise ValueError("EXACT_CAPABILITY_LIST_REQUIRED")
                return value
            if product == "runtime://braink/agent-skill-fabric" and operation == "register_skill":
                capabilities(payload.get("capabilities"))
            if product == "system://braink" and operation == "resolve_capability":
                query = payload.get("capability")
                if not isinstance(query, str) or not query.strip() or query != query.strip():
                    raise ValueError("EXACT_NONEMPTY_CAPABILITY_REQUIRED")
                matches = [p["id"] for p in self.products.values() if query in p.get("capabilities", [])]
                return {"status": "RESOLVED" if matches else "UNKNOWN", "matches": matches}
            if product == "runtime://braink/agent-skill-fabric" and operation == "resolve_task_capability":
                task = state["agents"]["tasks"][str(payload["id"])]
                query = task.get("required_capability")
                if not isinstance(query, str) or not query.strip() or query != query.strip():
                    raise ValueError("EXACT_NONEMPTY_CAPABILITY_REQUIRED")
                matches = [s["id"] for s in state["agents"]["skills"].values() if query in capabilities(s["capabilities"])]
                task["matches"] = matches
                task["state"] = "RESOLVED" if matches else "UNKNOWN"
                return task
            return super()._dispatch(state, product, operation, payload)
    return ExactCapabilityStore
