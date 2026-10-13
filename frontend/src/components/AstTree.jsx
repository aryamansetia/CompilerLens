import { useState } from "react";

/**
 * Draws the abstract syntax tree.
 *
 * The backend sends every node in the same shape, so one small recursive
 * component can draw the whole tree no matter how deep it goes.
 */

// Which colour family each kind of node belongs to.
const NODE_TONE = {
  Program: "root",
  Declaration: "statement",
  Assignment: "statement",
  ExpressionStatement: "statement",
  BinaryExpression: "operator",
  UnaryExpression: "operator",
  Identifier: "identifier",
  NumberLiteral: "literal",
  Type: "keyword",
  Value: "slot",
};

function TreeNode({ node }) {
  const [open, setOpen] = useState(true);
  const children = node.children || [];
  const hasChildren = children.length > 0;
  const tone = NODE_TONE[node.node_type] || "slot";

  return (
    <li>
      <span className={`ast-node ast-node--${tone}`}>
        {hasChildren && (
          <button
            className="ast-toggle"
            onClick={() => setOpen(!open)}
            aria-expanded={open}
            aria-label={open ? `Collapse ${node.label}` : `Expand ${node.label}`}
          >
            {open ? "−" : "+"}
          </button>
        )}
        <span className="ast-label">{node.label}</span>
        {node.detail && <span className="ast-detail">{node.detail}</span>}
      </span>
      {hasChildren && open && (
        <ul>
          {children.map((child, index) => (
            <TreeNode node={child} key={`${child.node_type}-${index}-${child.detail ?? ""}`} />
          ))}
        </ul>
      )}
    </li>
  );
}

export default function AstTree({ ast, astText }) {
  const [showText, setShowText] = useState(false);

  if (!ast) {
    return <p className="empty">No tree yet. Run the analysis to build one.</p>;
  }
  if (!ast.children.length) {
    return (
      <p className="empty">
        The parser could not build a tree from this program. Check the Errors tab to see why.
      </p>
    );
  }

  return (
    <div className="ast-view">
      <div className="ast-controls">
        <button className="link-button" onClick={() => setShowText(!showText)}>
          {showText ? "Show tree view" : "Show text view"}
        </button>
      </div>

      {showText ? (
        <pre className="ast-text">{astText}</pre>
      ) : (
        <ul className="tree">
          <TreeNode node={ast} />
        </ul>
      )}
    </div>
  );
}
