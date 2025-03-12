"use client";
import { Button } from "@/components/ui/button";
import { AutosizeTextarea } from "@/components/ui/textarea";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { Mic, Paperclip, Send } from "lucide-react";
import React, { useState } from "react";

interface MessageInputProps {
  onSendMessage: (content: string) => void;
  isLoading: boolean;
}

const MessageInput: React.FC<MessageInputProps> = ({ onSendMessage, isLoading }) => {
  const [message, setMessage] = useState("");

  const handleMessageChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setMessage(e.target.value);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim() && !isLoading) {
      onSendMessage(message);
      setMessage("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="p-4 absolute bottom-0 left-0 right-0 bg-transparent mb-4">
      <form onSubmit={handleSubmit} className="max-w-4xl mx-auto">
        <div className="relative flex items-center bg-background shadow-lg rounded-[2rem] border overflow-hidden h-full">
          <AutosizeTextarea placeholder="Ask a research question..." maxHeight={500} minHeight={52} className="pr-36 pl-6 py-4 font-medium border-none h-auto resize-none" value={message} onChange={handleMessageChange} onKeyDown={handleKeyDown} disabled={isLoading} rows={1} autoFocus />

          <div className="absolute right-3 flex items-center gap-2 h-full">
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button type="button" size="icon" variant="ghost" className="h-9 w-9" disabled={isLoading}>
                    <Paperclip className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Attach files (coming soon)</TooltipContent>
              </Tooltip>
            </TooltipProvider>

            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button type="button" size="icon" variant="ghost" className="h-9 w-9" disabled={isLoading}>
                    <Mic className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Voice input (coming soon)</TooltipContent>
              </Tooltip>
            </TooltipProvider>

            <Button type="submit" size="icon" className="h-9 w-9 rounded-full" disabled={isLoading || !message.trim()}>
              <Send className="h-4 w-4" />
              <span className="sr-only">Send message</span>
            </Button>
          </div>
        </div>
      </form>
    </div>
  );
};

export default MessageInput;
