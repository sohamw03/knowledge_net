"use client";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useChatContext } from "@/lib/store/ChatContext";
import { Message as MessageType } from "@/lib/types";
import { v4 as uuidv4 } from "uuid";
import React, { useEffect, useRef, useState } from "react";
import Message from "./Message";

interface ChatHistoryProps {
  messages: MessageType[];
  isLoading: boolean;
}

// Traditional prop-based component
const ChatHistory: React.FC<ChatHistoryProps> = ({ messages, isLoading }) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [lastProgressMessage, setLastProgressMessage] = useState<string>("");

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="pb-24 overflow-auto focus-visible:outline-0" tabIndex={-1}>
      {messages.length === 0 ? (
        <div className="h-full flex flex-col items-center justify-center p-8 text-center">
          <div className="max-w-md space-y-2">
            <h2 className="text-2xl font-bold">Welcome to the KNet demo</h2>
            <p className="text-muted-foreground">Ask any research question to get started. The assistant will provide detailed answers backed by research and sources.</p>
          </div>
        </div>
      ) : (
        messages.map((message) => {
          return <Message key={message.id} message={message} lastProgressMessage={lastProgressMessage} setLastProgressMessage={setLastProgressMessage} />;
        })
      )}

      <div ref={messagesEndRef} />
    </div>
  );
};

// Context-based component
export const ChatHistoryWithContext: React.FC = () => {
  const { chatState } = useChatContext();
  return <ChatHistory messages={chatState.messages} isLoading={chatState.isLoading} />;
};

export default ChatHistory;
