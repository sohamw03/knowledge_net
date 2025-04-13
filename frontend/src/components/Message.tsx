import { Avatar } from "@/components/ui/avatar";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { Message as MessageType } from "@/lib/types";
import { Bot, Copy, MoreHorizontal, User2 } from "lucide-react";
import React, { useState, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/cjs/styles/prism";

// ImageGallery component for handling images in a scrollable container
const ImageGallery = ({ imageUrls }: { imageUrls: string[] }) => {
  const [loadedImages, setLoadedImages] = useState<string[]>([]);

  // Lazy load images using Intersection Observer
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const img = entry.target as HTMLImageElement;
            const src = img.getAttribute("data-src");
            if (src) {
              img.src = src;
              observer.unobserve(img);
              setLoadedImages((prev) => [...prev, src]);
            }
          }
        });
      },
      { rootMargin: "100px" }
    );

    const imgPlaceholders = document.querySelectorAll(".lazy-image");
    imgPlaceholders.forEach((img) => observer.observe(img));

    return () => observer.disconnect();
  }, [imageUrls]);

  if (!imageUrls || imageUrls.length === 0) return null;

  return (
    <div className="mt-4 mb-4">
      <h3 className="text-md font-semibold mb-2">Relevant Images:</h3>
      <ScrollArea className="w-full max-h-72 rounded-md border">
        <div className="p-2 space-y-3">
          {imageUrls.map((url, index) => (
            <div key={index} className="image-container">
              <img
                className="lazy-image rounded-md max-w-full"
                src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='100' height='100' viewBox='0 0 100 100'%3E%3Crect width='100' height='100' fill='%23f1f1f1'/%3E%3C/svg%3E"
                data-src={url}
                alt={`Research image ${index + 1}`}
                loading="lazy"
                onError={(e) => {
                  const target = e.target as HTMLImageElement;
                  target.onerror = null;
                  target.src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='100' height='100' viewBox='0 0 100 100'%3E%3Crect width='100' height='100' fill='%23f1f1f1'/%3E%3Ctext x='50%' y='50%' font-size='12' text-anchor='middle' alignment-baseline='middle' font-family='Arial, sans-serif'%3EImage failed to load%3C/text%3E%3C/svg%3E";
                }}
              />
            </div>
          ))}
        </div>
      </ScrollArea>
    </div>
  );
};

const MarkdownComponents: Record<string, React.ComponentType<any>> = {
  h1: ({ children }) => <h1 className="text-2xl font-bold mb-4">{children}</h1>,
  h2: ({ children }) => <h2 className="text-xl font-bold mb-3">{children}</h2>,
  h3: ({ children }) => <h3 className="text-lg font-bold mb-3">{children}</h3>,
  p: ({ children }) => <p className="mb-4 last:mb-0">{children}</p>,
  ul: ({ children }) => <ul className="list-disc ml-6 mb-4">{children}</ul>,
  ol: ({ children }) => <ol className="list-decimal ml-6 mb-4">{children}</ol>,
  li: ({ children }) => <li className="mb-1">{children}</li>,
  code: ({ node, inline, className, children, ...props }) => {
    const match = /language-(\w+)/.exec(className || "");
    const language = match ? match[1] : "";

    return Object.keys(node.properties).length === 0 ? (
      <code className="bg-muted px-1 py-0.5 rounded-md text-sm" {...props}>
        {children}
      </code>
    ) : (
      <ScrollArea className="w-full max-w-full">
        <SyntaxHighlighter
          style={oneDark}
          language={language || "text"}
          PreTag="div"
          className="rounded-md my-2 text-sm"
          showLineNumbers
          customStyle={{
            margin: 0,
            borderRadius: "0.5rem",
            padding: "1rem",
          }}
          {...props}>
          {String(children).replace(/\n$/, "")}
        </SyntaxHighlighter>
      </ScrollArea>
    );
  },
  pre: ({ children }) => <div className="bg-transparent p-0 max-w-full">{children}</div>,
  a: ({ children, href }) => (
    <a href={href} className="text-primary hover:underline" target="_blank" rel="noopener noreferrer">
      {children}
    </a>
  ),
  blockquote: ({ children }) => <blockquote className="border-l-4 border-border pl-4 italic my-4">{children}</blockquote>,
  table: ({ children }) => (
    <div className="overflow-x-auto border rounded-2xl my-4">
      <table className="w-full border-collapse rounded-2xl overflow-hidden shadow-sm">{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead className="bg-muted">{children}</thead>,
  tbody: ({ children }) => <tbody>{children}</tbody>,
  th: ({ children }) => <th className="border-r last:border-r-0 border-slate-900 px-4 py-2 text-left font-semibold">{children}</th>,
  tr: ({ children }) => <tr className="border-b last:border-b-0 border-border">{children}</tr>,
  td: ({ children }) => <td className="border-r last:border-r-0 border-border px-4 py-2">{children}</td>,
};

const Message = ({ message }: { message: MessageType }) => {
  const isUser = message.role === "user";
  const isProgress = message.content.includes("%)") && message.role === "assistant";
  const [imageUrls, setImageUrls] = useState<string[]>([]);

  // Extract image URLs from the message content or use the media object
  useEffect(() => {
    if (!isUser && !isProgress) {
      let urls: string[] = [];

      // First, check if there's a media object with images
      if (message.media?.images && message.media.images.length > 0) {
        urls = message.media.images;
      } else {
        // Fallback to extracting from markdown content
        const imgRegex = /!\[.*?\]\((.*?)\)/g;
        let match;

        while ((match = imgRegex.exec(message.content)) !== null) {
          if (match[1]) {
            urls.push(match[1]);
          }
        }
      }

      setImageUrls(urls);
    }
  }, [message.content, message.media, isUser, isProgress]);

  // Prepare message content without image markdown
  const cleanContent = message.content.replace(/!\[.*?\]\(.*?\)\n?/g, "").replace(/\*\*Relevant Images:\*\*\n/g, "");

  const copyToClipboard = () => {
    navigator.clipboard.writeText(message.content);
  };

  return (
    <div className="py-2 px-4">
      <div className={`max-w-2xl mx-auto flex gap-4 relative ${isUser ? "flex-row-reverse" : ""}`}>
        <Avatar className={`h-8 w-8 shrink-0 absolute justify-center item-center ${isUser ? "-right-12" : "-left-12"} top-0`}>{isUser ? <User2 className="h-5 w-5" /> : <Bot className="h-5 w-5" />}</Avatar>

        <div className={`max-w-2xl flex-1 ${isUser ? "items-end" : "items-start"}`}>
          <div className={`flex items-center gap-2 mb-1 ${isUser ? "justify-end" : "justify-start"}`}>
            {isUser && <div className="text-xs text-muted-foreground">{new Date(message.timestamp).toLocaleTimeString()}</div>}
            <div className="font-medium">{isUser ? "You" : "KNet"}</div>
            {!isUser && <div className="text-xs text-muted-foreground">{new Date(message.timestamp).toLocaleTimeString()}</div>}

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
              {cleanContent}
            </ReactMarkdown>

            {imageUrls.length > 0 && <ImageGallery imageUrls={imageUrls} />}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Message;
