import { Avatar } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { Message as MessageType } from "@/lib/types";
import { Bot, Copy, MoreHorizontal, User2 } from "lucide-react";
import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const MarkdownComponents: Record<string, React.ComponentType<any>> = {
  h1: ({ children }) => <h1 className="text-2xl font-bold mb-4">{children}</h1>,
  h2: ({ children }) => <h2 className="text-xl font-bold mb-3">{children}</h2>,
  h3: ({ children }) => <h3 className="text-lg font-bold mb-3">{children}</h3>,
  p: ({ children }) => <p className="mb-4 last:mb-0">{children}</p>,
  ul: ({ children }) => <ul className="list-disc ml-6 mb-4">{children}</ul>,
  ol: ({ children }) => <ol className="list-decimal ml-6 mb-4">{children}</ol>,
  li: ({ children }) => <li className="mb-1">{children}</li>,
  code: ({ node, inline, className, children, ...props }) => (
    <code className={`${inline ? "bg-muted px-1 py-0.5 rounded-md text-sm" : "block bg-muted/50 p-3 rounded-lg text-sm overflow-x-auto"}`} {...props}>
      {children}
    </code>
  ),
  pre: ({ children }) => <pre className="bg-transparent p-0">{children}</pre>,
  a: ({ children, href }) => (
    <a href={href} className="text-primary hover:underline" target="_blank" rel="noopener noreferrer">
      {children}
    </a>
  ),
  blockquote: ({ children }) => <blockquote className="border-l-4 border-border pl-4 italic my-4">{children}</blockquote>,
  table: ({ children }) => <table className="w-full border-collapse my-4 border-slate-300 dark:border-slate-200">{children}</table>,
  thead: ({ children }) => <thead className="bg-muted/50">{children}</thead>,
};

interface MessageProps {
  message: MessageType;
}

const Message: React.FC<MessageProps> = ({ message }) => {
  const isUser = message.role === "user";
  const isProgress = message.content.includes("%)") && message.role === "assistant";

  const copyToClipboard = () => {
    navigator.clipboard.writeText(message.content);
  };

  return (
    <div className="py-2 px-4">
      <div className={`max-w-2xl mx-auto flex gap-4 relative ${isUser ? "flex-row-reverse" : ""}`}>
        <Avatar className={`h-8 w-8 shrink-0 absolute justify-center item-center ${isUser ? "-right-12" : "-left-12"} top-0`}>{isUser ? <User2 className="h-5 w-5" /> : <Bot className="h-5 w-5" />}</Avatar>

        <div className={`flex-1 ${isUser ? "items-end" : "items-start"}`}>
          <div className={`flex items-center gap-2 mb-1 ${isUser ? "justify-end" : "justify-start"}`}>
            <div className="text-xs text-muted-foreground">{new Date(message.timestamp).toLocaleTimeString()}</div>
            <div className="font-medium">{isUser ? "You" : "Research Assistant"}</div>

            {!isUser && (
              <div className="ml-auto flex items-center gap-2">
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button size="icon" variant="ghost" className="h-8 w-8" onClick={copyToClipboard}>
                        <Copy className="h-4 w-4" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>Copy to clipboard</TooltipContent>
                  </Tooltip>
                </TooltipProvider>

                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button size="icon" variant="ghost" className="h-8 w-8">
                      <MoreHorizontal className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem onClick={copyToClipboard}>Copy text</DropdownMenuItem>
                    <DropdownMenuItem>Show sources</DropdownMenuItem>
                    <DropdownMenuItem>View in visualizations</DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            )}
          </div>

          <div className={`mt-1 max-w-none ${isUser ? "bg-slate-300 dark:bg-slate-200 dark:text-background text-foreground" : isProgress ? "bg-muted/30" : "bg-muted/50"} p-3 rounded-2xl ${isUser ? "rounded-tr-sm" : "rounded-tl-sm"}`} style={{ overflowWrap: "anywhere" }}>
            <ReactMarkdown remarkPlugins={[remarkGfm]} components={MarkdownComponents}>
              {message.content}
            </ReactMarkdown>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Message;
