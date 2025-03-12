"use client";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Message as MessageType } from "@/lib/types";
import { Loader2 } from "lucide-react";
import React, { useEffect, useRef } from "react";
import Message from "./Message";

interface ChatHistoryProps {
  messages: MessageType[];
  isLoading: boolean;
}

const ChatHistory: React.FC<ChatHistoryProps> = ({ messages, isLoading }) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <ScrollArea tabIndex={-1}>
      <div className="pb-24 focus-visible:outline-0" tabIndex={-1}>
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center p-8 text-center">
            <div className="max-w-md space-y-2">
              <h2 className="text-2xl font-bold">Welcome to the KNet demo</h2>
              <p className="text-muted-foreground">Ask any research question to get started. The assistant will provide detailed answers backed by research and sources.</p>
            </div>
          </div>
        ) : (
          messages.map((message) => <Message key={message.id} message={message} />)
        )}

        {isLoading && (
          <div className="my-2 mx-4">
            <div className="max-w-2xl mx-auto flex gap-4 relative">
              <div className="h-8 w-8 rounded-full shrink-0 bg-muted flex items-center justify-center absolute -left-12 top-0">
                <Loader2 className="h-5 w-5 animate-spin" />
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <div className="font-medium">KNet</div>
                  <div className="text-xs text-muted-foreground">Just now</div>
                </div>
                <div className="mt-1 bg-muted/50 p-3 rounded-2xl rounded-tl-sm">
                  <div className="flex space-x-2">
                    <div className="w-2 h-2 rounded-full bg-muted-foreground/30 animate-pulse"></div>
                    <div className="w-2 h-2 rounded-full bg-muted-foreground/30 animate-pulse" style={{ animationDelay: "300ms" }}></div>
                    <div className="w-2 h-2 rounded-full bg-muted-foreground/30 animate-pulse" style={{ animationDelay: "600ms" }}></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>
    </ScrollArea>
  );
};

export default ChatHistory;
