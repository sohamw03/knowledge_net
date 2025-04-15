import { Avatar } from "@/components/ui/avatar";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { Message as MessageType, ResearchTree } from "@/lib/types";
import { Bot, Copy, MoreHorizontal, User2, ExternalLink, Loader2, SearchIcon } from "lucide-react";
import React, { useState, useEffect, useMemo, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/cjs/styles/prism";
import { Badge } from "@/components/ui/badge";

// Function to extract all source URLs from the research tree
const extractAllSources = (tree: ResearchTree | undefined): Array<{ text: string; url: string }> => {
  if (!tree) return [];

  // Start with an empty set to avoid duplicates
  const uniqueSources = new Set<string>();

  // Recursive function to gather all sources
  const collectSources = (node: ResearchTree) => {
    // Add all sources from the current node
    if (node.sources && Array.isArray(node.sources)) {
      node.sources.forEach((url) => uniqueSources.add(url));
    }

    // Process all children recursively
    if (node.children && Array.isArray(node.children)) {
      node.children.forEach((child) => collectSources(child));
    }
  };

  // Start the collection process
  collectSources(tree);

  // Convert the set to an array of objects with text and url properties
  return Array.from(uniqueSources).map((url) => {
    // Try to extract a readable title from the URL
    let text = "";
    try {
      const urlObj = new URL(url);
      // Remove 'www.' if present and take the hostname
      text = urlObj.hostname.replace(/^www\./, "");

      // Add the pathname if it's not just "/"
      if (urlObj.pathname && urlObj.pathname !== "/") {
        // Format the pathname - keep it short and clean
        const path = urlObj.pathname.split("/").filter(Boolean);
        if (path.length > 0) {
          const lastPathSegment = path[path.length - 1]
            .replace(/[-_]/g, " ") // Replace dashes and underscores with spaces
            .replace(/\.html$|\.pdf$|\.php$/, ""); // Remove common extensions

          text = `${text} - ${lastPathSegment}`;
        }
      }
    } catch (e) {
      // If URL parsing fails, use the URL as is
      text = url;
    }

    return { text, url };
  });
};

// SourceLinks component for displaying research sources in a scrollable container
const SourceLinks = ({ links }: { links: Array<{ text: string; url: string }> }) => {
  if (!links || links.length === 0) return null;

  return (
    <div className="mt-4 mb-4">
      <h3 className="text-md font-semibold mb-2">Research Sources:</h3>
      <ScrollArea className="w-full h-[300px] overflow-auto border border-slate-200 dark:border-slate-700 rounded-xl shadow-sm p-1" type="always">
        <div className="space-y-2">
          {links.map((link, index) => {
            // Extract domain for display
            let domain = "";
            try {
              const urlObj = new URL(link.url);
              domain = urlObj.hostname.replace(/^www\./, "");
            } catch (e) {
              domain = "Unknown source";
            }

            return (
              <div key={index} className="flex items-start gap-2 group hover:bg-muted/50 p-2 rounded-md transition-colors">
                <ExternalLink className="h-4 w-4 text-muted-foreground flex-shrink-0 mt-1" />
                <div className="flex-1">
                  <a href={link.url} className="text-primary hover:underline text-sm block" target="_blank" rel="noopener noreferrer">
                    {domain}
                  </a>
                  <a href={link.url} className="text-xs text-muted-foreground hover:underline block truncate" target="_blank" rel="noopener noreferrer" title={link.url}>
                    {link.url}
                  </a>
                </div>
                <div className="opacity-0 group-hover:opacity-100 transition-opacity">
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-6 w-6 p-0"
                          onClick={(e) => {
                            e.preventDefault();
                            navigator.clipboard.writeText(link.url);
                          }}>
                          <Copy className="h-3 w-3" />
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent>Copy link</TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                </div>
              </div>
            );
          })}
        </div>
      </ScrollArea>
    </div>
  );
};

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
      <ScrollArea className="w-full h-[300px] overflow-auto border border-slate-200 dark:border-slate-700 rounded-xl shadow-sm p-1" type="always">
        <div className="p-2 grid grid-cols-2 md:grid-cols-4 gap-2">
          {imageUrls.map((url, index) => (
            <div key={index} className="image-container h-[150px]">
              <img
                className="lazy-image rounded-md w-full h-full object-cover shadow-sm border border-slate-100 dark:border-slate-800"
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
    <div className="overflow-x-scroll border rounded-2xl my-4">
      <table className="w-max border-collapse rounded-2xl overflow-hidden shadow-sm">{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead className="bg-muted">{children}</thead>,
  tbody: ({ children }) => <tbody>{children}</tbody>,
  th: ({ children }) => <th className="border-r last:border-r-0 border-slate-900 px-2 py-1 text-left font-semibold">{children}</th>,
  tr: ({ children }) => <tr className="border-b last:border-b-0 border-border">{children}</tr>,
  td: ({ children }) => <td className="border-r last:border-r-0 border-border px-2 py-1">{children}</td>,
};

interface MessageProps {
  message: MessageType;
  isLoading?: boolean;
  lastProgressMessage?: string;
  setLastProgressMessage?: React.Dispatch<React.SetStateAction<string>>;
}

const Message = ({ message, isLoading, lastProgressMessage, setLastProgressMessage }: MessageProps) => {
  const isUser = message?.role === "user";
  const [imageUrls, setImageUrls] = useState<string[]>([]);
  const progressPercentage = message.progress || 0;
  const isProgressMessage = message.isProgress === true;
  const [isSearchMessage, setIsSearchMessage] = useState(message.content.startsWith("s_"));

  // Use useMemo to extract sources only once and only when they change
  const sourceLinks = useMemo(() => {
    // If this is the loading component, return empty sources
    if (isLoading) return [];

    // First, extract sources from the research_tree if available
    const researchSources = extractAllSources(message.research_tree);

    // If research_tree sources exist, use those
    if (researchSources.length > 0) {
      return researchSources;
    }

    // Otherwise, fall back to any links in the media object
    return message.media?.links || [];
  }, [message.research_tree, message.media?.links, isLoading]);

  // Extract image URLs from the message content or use the media object
  useEffect(() => {
    if (isLoading) {
      setImageUrls([]);
      return;
    }

    if (!isUser) {
      // Handle image URLs
      let urls: string[] = [];

      // First, check if there's a media object with images
      if (message.media?.images && message.media.images.length > 0) {
        urls = message.media.images;
      }
      setImageUrls(urls);
    }

    setIsSearchMessage(message.content.startsWith("s_"));
    if ((isLoading || isProgressMessage) && !message.content.startsWith("s_")) {
      setLastProgressMessage!(message.content);
    }
  }, [message.content, message.media, isUser, isLoading, isProgressMessage, setLastProgressMessage]);

  const copyToClipboard = () => {
    if (!isLoading) {
      navigator.clipboard.writeText(message.content);
    }
  };

  return (
    <div className="py-2 px-2 sm:px-4 sm:mx-12">
      <div className={`w-full flex gap-4 relative ${isUser ? "justify-end" : "justify-start"}`}>
        <Avatar className={`h-8 w-8 rounded-full bg-muted flex justify-center item-center absolute ${isUser ? "right-0 sm:-right-12" : "left-0 sm:-left-12"} top-0 hidden sm:flex`}>{isLoading || isProgressMessage ? <Loader2 className="h-full w-6 animate-spin" /> : isUser ? <User2 className="h-full w-6" /> : <Bot className="h-full w-6" />}</Avatar>

        <div className={`max-w-full ${isLoading || isProgressMessage ? "w-[80%]" : ""} ${isUser ? "items-end ml-auto" : "items-start mr-auto"}`}>
          <div className={`flex items-center gap-2 mb-1 ${isUser ? "justify-end" : "justify-start"}`}>
            <div className="font-medium">{isUser ? "You" : "KNet"}</div>
            {!isUser && !isLoading && <div className="text-xs text-muted-foreground">{new Date(message.timestamp).toLocaleTimeString()}</div>}
            {isLoading && <div className="text-xs text-muted-foreground">Just now</div>}

            {!isUser && !isLoading && !isProgressMessage && (
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

          <div className={`mt-1 w-full ${isUser ? "bg-slate-300 dark:bg-slate-200 dark:text-background text-foreground" : "bg-muted/50"} p-3 rounded-2xl ${isUser ? "rounded-tr-sm" : "rounded-tl-sm"}`} style={{ overflowWrap: "anywhere" }}>
            {isLoading || isProgressMessage ? (
              <div className="space-y-2">
                <div>{lastProgressMessage}</div>
                <div className={`flex items-center ${isSearchMessage ? "justify-between" : "justify-end"} text-sm w-full`}>
                  {isSearchMessage ? (
                    <Badge variant="outline" className="bg-primary/20 text-primary rounded-full">
                      <SearchIcon className="h-3 w-3 mr-1" />
                      {message.content.slice(2)}
                    </Badge>
                  ) : null}
                  <Badge variant="outline" className="ml-2 bg-primary/20 text-primary">
                    {progressPercentage}%
                  </Badge>
                </div>
                <div className="w-full bg-muted/30 h-2.5 rounded-full overflow-hidden">
                  <div className="h-full bg-primary transition-all duration-500 rounded-full flex items-center justify-end" style={{ width: `${progressPercentage}%` }}>
                    <div className="h-2 w-2 rounded-full bg-primary-foreground mr-0.5 animate-pulse"></div>
                  </div>
                </div>
              </div>
            ) : (
              <>
                <ReactMarkdown remarkPlugins={[remarkGfm]} components={MarkdownComponents}>
                  {message.content}
                </ReactMarkdown>

                {sourceLinks.length > 0 && <SourceLinks links={sourceLinks} />}
                {imageUrls.length > 0 && <ImageGallery imageUrls={imageUrls} />}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Message;
