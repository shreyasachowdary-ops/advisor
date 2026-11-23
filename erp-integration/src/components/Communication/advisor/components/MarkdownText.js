import { Fragment } from "react";
import { parseMarkdown } from "../markdown";

function Inlines({ parts }) {
  return parts.map((part, index) => {
    if (part.bold) return <strong key={index}>{part.text}</strong>;
    if (part.italic) return <em key={index}>{part.text}</em>;
    return <Fragment key={index}>{part.text}</Fragment>;
  });
}

/** Renders advisor answer Markdown as React elements (no dangerouslySetInnerHTML). */
export default function MarkdownText({ text }) {
  const blocks = parseMarkdown(text);
  return (
    <div className="answer-markdown">
      {blocks.map((block, index) => {
        if (block.type === "heading") {
          return (
            <h3 className="answer-heading" key={index}>
              <Inlines parts={block.inlines} />
            </h3>
          );
        }
        if (block.type === "ul" || block.type === "ol") {
          const List = block.type;
          return (
            <List className="answer-list" key={index}>
              {block.items.map((item, itemIndex) => (
                <li key={itemIndex}>
                  <Inlines parts={item} />
                </li>
              ))}
            </List>
          );
        }
        return (
          <p className="answer-lead" key={index}>
            {block.lines.map((line, lineIndex) => (
              <Fragment key={lineIndex}>
                {lineIndex > 0 && <br />}
                <Inlines parts={line} />
              </Fragment>
            ))}
          </p>
        );
      })}
    </div>
  );
}
