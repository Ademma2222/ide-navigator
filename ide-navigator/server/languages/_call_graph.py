from lsprotocol import types

class CallGraphMixin:
    _GRAPH_KIND_MAP = {
        types.SymbolKind.Function: "function",
        types.SymbolKind.Method: "method",
        types.SymbolKind.Constructor: "constructor",
        types.SymbolKind.Class: "class",
        types.SymbolKind.Interface: "interface",
        types.SymbolKind.Struct: "struct",
    }

    _GRAPH_ALLOWED_TYPES = frozenset({
        "function", "method", "constructor", "class", "interface", "struct",
    })

    _GRAPH_MAX_LABEL_LEN = 120

    _BRANCH_NODE_TYPES = frozenset({
        "if_statement", "elif_clause",
        "for_statement", "for_in_statement", "for_of_statement",
        "for_range_loop",
        "while_statement", "do_statement", "do_while_statement",
        "case_statement", "case_clause", "switch_case",
        "switch_block_statement_group",
        "expression_case", "type_case", "communication_case",
        "except_clause", "catch_clause",
        "conditional_expression", "ternary_expression",
        "select_statement",
    })

    def get_call_graph(self, source: str, uri: str | None = None) -> dict:
        tree = self._parse(source, uri)
        root = tree.root_node

        symbols = self._extract_symbols(root)

        symbol_info: dict[str, dict] = {}
        self._collect_symbol_info(symbols, symbol_info)

        known_funcs: set[str] = set()
        self._collect_callable_names(symbols, known_funcs)

        short_to_fqn: dict[str, list[str]] = {}
        for fqn in known_funcs:
            short = fqn.rsplit(".", 1)[-1]
            short_to_fqn.setdefault(short, []).append(fqn)

        contain_edges: set[tuple[str, str]] = set()
        self._collect_class_edges(symbols, contain_edges)

        call_edges: set[tuple[str, str]] = set()
        self._walk_calls(root, None, known_funcs, call_edges, short_to_fqn)

        complexity_map: dict[str, int] = {}
        self._collect_complexity(root, complexity_map)

        container_types = ("class", "interface", "struct")
        all_ids = known_funcs | {
            n for n, info in symbol_info.items() if info["type"] in container_types
        }

        def safe_label(name: str) -> str:
            return name[:self._GRAPH_MAX_LABEL_LEN]

        def safe_type(raw_type: str) -> str:
            return raw_type if raw_type in self._GRAPH_ALLOWED_TYPES else "function"

        nodes = []
        for n in sorted(all_ids):
            info = symbol_info.get(n, {})
            node = {
                "id": safe_label(n),
                "label": safe_label(info.get("label", n)),
                "type": safe_type(info.get("type", "function")),
            }
            rng = info.get("range")
            if rng is not None:
                node["line"] = rng.start.line
                node["character"] = rng.start.character
                node["endLine"] = rng.end.line
                node["endCharacter"] = rng.end.character
            if n in complexity_map:
                node["complexity"] = complexity_map[n]
            nodes.append(node)

        edge_list: list[dict] = []
        for a, b in sorted(call_edges):
            edge_list.append({
                "from": safe_label(a), "to": safe_label(b), "kind": "call",
            })
        for a, b in sorted(contain_edges):
            edge_list.append({
                "from": safe_label(a), "to": safe_label(b), "kind": "contains",
            })

        return {"nodes": nodes, "edges": edge_list}

    def _collect_class_edges(
        self, symbols: list[types.DocumentSymbol], edges: set[tuple[str, str]],
        prefix: str = "",
    ) -> None:
        for s in symbols:
            fqn = f"{prefix}.{s.name}" if prefix else s.name
            if s.kind in (types.SymbolKind.Class, types.SymbolKind.Interface,
                          types.SymbolKind.Struct) and s.children:
                for child in s.children:
                    child_fqn = f"{fqn}.{child.name}"
                    if child.kind in (types.SymbolKind.Function, types.SymbolKind.Method,
                                      types.SymbolKind.Constructor):
                        edges.add((fqn, child_fqn))
            if s.children:
                self._collect_class_edges(s.children, edges, fqn)

    def _collect_symbol_info(
        self, symbols: list[types.DocumentSymbol], result: dict[str, dict],
        prefix: str = "",
    ) -> None:
        for s in symbols:
            fqn = f"{prefix}.{s.name}" if prefix else s.name
            kind_str = self._GRAPH_KIND_MAP.get(s.kind)
            if kind_str and fqn not in result:
                result[fqn] = {
                    "type": kind_str,
                    "range": s.selection_range,
                    "label": s.name,
                }
            if s.children:
                self._collect_symbol_info(s.children, result, fqn)

    def _collect_callable_names(
        self, symbols: list[types.DocumentSymbol], result: set[str],
        prefix: str = "",
    ) -> None:
        for s in symbols:
            fqn = f"{prefix}.{s.name}" if prefix else s.name
            if s.kind in (types.SymbolKind.Function, types.SymbolKind.Method,
                          types.SymbolKind.Constructor):
                result.add(fqn)
            if s.children:
                self._collect_callable_names(s.children, result, fqn)

    def _collect_complexity(self, root, result: dict[str, int],
                            scope: str = "") -> None:
        stack: list[tuple] = [(root, scope)]
        while stack:
            node, cur_scope = stack.pop()
            name = self._get_func_def_name(node)
            if name is not None:
                fqn = f"{cur_scope}.{name}" if cur_scope else name
                result[fqn] = self._compute_complexity(node)
                for child in node.children:
                    stack.append((child, fqn))
            else:
                cls_name = self._get_class_def_name(node)
                if cls_name:
                    child_scope = f"{cur_scope}.{cls_name}" if cur_scope else cls_name
                else:
                    child_scope = cur_scope
                for child in node.children:
                    stack.append((child, child_scope))

    def _compute_complexity(self, func_node) -> int:
        count = 1
        stack = [func_node]
        while stack:
            node = stack.pop()
            if node.type in self._BRANCH_NODE_TYPES:
                count += 1
            for child in node.children:
                stack.append(child)
        return count

    def _walk_calls(
        self, node, current_func: str | None,
        known: set[str], edges: set[tuple[str, str]],
        short_to_fqn: dict[str, list[str]] | None = None,
        scope: str = "",
    ) -> None:
        func_name = self._get_func_def_name(node)
        cls_name = self._get_class_def_name(node) if func_name is None else None

        if func_name is not None:
            current_func = f"{scope}.{func_name}" if scope else func_name
            scope = current_func
        elif cls_name is not None:
            scope = f"{scope}.{cls_name}" if scope else cls_name

        if current_func is not None:
            callee = self._get_call_name(node)
            if callee:
                resolved = False
                if short_to_fqn and callee in short_to_fqn:
                    for fqn in short_to_fqn[callee]:
                        edges.add((current_func, fqn))
                        resolved = True
                if not resolved and callee in known:
                    edges.add((current_func, callee))

        for child in node.children:
            self._walk_calls(child, current_func, known, edges, short_to_fqn, scope)

    def _get_class_def_name(self, node) -> str | None:
        if node.type in (
            "class_definition", "class_declaration",
            "interface_declaration", "struct_specifier",
            "type_spec",
        ):
            name_node = node.child_by_field_name("name")
            if name_node:
                return name_node.text.decode("utf-8")
        return None

    def _get_func_def_name(self, node) -> str | None:
        if node.type in (
            "function_definition", "function_declaration",
            "method_definition", "method_declaration",
            "constructor_declaration",
        ):
            name_node = node.child_by_field_name("name")
            if name_node:
                return name_node.text.decode("utf-8")
        return None

    def _find_func_node_at(self, root, line: int, character: int):
        node = root.descendant_for_point_range((line, character), (line, character))
        while node is not None:
            if self._get_func_def_name(node) is not None:
                return node
            node = node.parent
        return None

    def _get_call_name(self, node) -> str | None:
        if node.type not in ("call", "call_expression", "method_invocation"):
            return None

        func_node = (
            node.child_by_field_name("function")
            or node.child_by_field_name("name")
        )
        if func_node is None:
            return None

        if func_node.type in ("identifier", "field_identifier", "property_identifier"):
            return func_node.text.decode("utf-8")

        if func_node.type in ("attribute", "member_expression",
                              "selector_expression", "field_expression"):
            attr = (
                func_node.child_by_field_name("attribute")
                or func_node.child_by_field_name("property")
                or func_node.child_by_field_name("field")
            )
            if attr:
                return attr.text.decode("utf-8")

        return None
