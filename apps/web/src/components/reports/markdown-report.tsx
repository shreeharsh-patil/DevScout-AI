"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface MarkdownReportProps {
  content: string;
}

export default function MarkdownReport({ content }: MarkdownReportProps) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        h1: ({ children }) => (
          <h1 className="text-2xl font-bold text-white mb-6 border-b border-neutral-800 pb-2">
            {children}
          </h1>
        ),
        h2: ({ children }) => (
          <h2 className="text-xl font-semibold text-indigo-400 mt-8 mb-4">{children}</h2>
        ),
        h3: ({ children }) => (
          <h3 className="text-lg font-medium text-emerald-400 mt-6 mb-2">{children}</h3>
        ),
        h4: ({ children }) => (
          <h4 className="text-base font-medium text-neutral-300 mt-4 mb-2">{children}</h4>
        ),
        p: ({ children }) => (
          <p className="text-neutral-300 mb-3 leading-relaxed">{children}</p>
        ),
        ul: ({ children }) => (
          <ul className="mb-4 space-y-1 ml-2">{children}</ul>
        ),
        ol: ({ children }) => (
          <ol className="mb-4 space-y-1 ml-4 list-decimal">{children}</ol>
        ),
        li: ({ children }) => (
          <li className="flex gap-2 text-neutral-300">
            <span className="text-indigo-400 shrink-0 mt-0.5">•</span>
            <span>{children}</span>
          </li>
        ),
        strong: ({ children }) => (
          <strong className="text-white font-semibold">{children}</strong>
        ),
        em: ({ children }) => (
          <em className="text-neutral-400 italic">{children}</em>
        ),
        a: ({ href, children }) => (
          <a
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className="text-indigo-400 hover:underline"
          >
            {children}
          </a>
        ),
        blockquote: ({ children }) => (
          <blockquote className="border-l-2 border-indigo-500 pl-4 my-4 text-neutral-400 italic">
            {children}
          </blockquote>
        ),
        table: ({ children }) => (
          <div className="overflow-x-auto my-6">
            <table className="w-full text-sm border-collapse">{children}</table>
          </div>
        ),
        thead: ({ children }) => (
          <thead className="bg-neutral-900 text-neutral-400 text-xs uppercase">{children}</thead>
        ),
        tbody: ({ children }) => (
          <tbody className="divide-y divide-neutral-800">{children}</tbody>
        ),
        tr: ({ children }) => <tr className="hover:bg-neutral-900/50">{children}</tr>,
        th: ({ children }) => (
          <th className="px-4 py-2 text-left font-medium text-neutral-400">{children}</th>
        ),
        td: ({ children }) => (
          <td className="px-4 py-3 text-neutral-300">{children}</td>
        ),
        code: ({ className, children, ...props }) => {
          const isBlock = className?.includes("language-");
          return isBlock ? (
            <code
              className="block bg-neutral-900 border border-neutral-800 rounded-lg p-4 text-sm font-mono text-emerald-300 overflow-x-auto my-4"
              {...props}
            >
              {children}
            </code>
          ) : (
            <code
              className="bg-neutral-900 text-emerald-300 px-1.5 py-0.5 rounded text-xs font-mono"
              {...props}
            >
              {children}
            </code>
          );
        },
        pre: ({ children }) => <pre className="not-prose">{children}</pre>,
        hr: () => <hr className="border-neutral-800 my-6" />,
      }}
    >
      {content}
    </ReactMarkdown>
  );
}
