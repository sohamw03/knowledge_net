"use client";
import { Button } from "@/components/ui/button";
import { MessageSquare, PlusCircle } from "lucide-react";
import React from "react";

interface Conversation {
  id: string;
  title: string;
  lastUpdated: string;
  active?: boolean;
}

interface ConversationListProps {
  conversations: Conversation[];
  onNewConversation: () => void;
  onSelectConversation: (id: string) => void;
}

const ConversationList: React.FC<ConversationListProps> = ({ conversations, onNewConversation, onSelectConversation }) => {
  const handleSelectConversation = (id: string) => {
    onSelectConversation(id);
  };

  return (
    <div className="flex flex-col h-full py-2">
      <div className="px-4 py-2">
        <Button onClick={onNewConversation} className="w-full justify-start" variant="outline">
          <PlusCircle className="mr-2 h-4 w-4" />
          New Research
        </Button>
      </div>

      <div className="px-2 py-2">
        <h2 className="text-sm font-semibold px-2 mb-2">Recent Research</h2>
        <div className="space-y-1">
          {conversations.length === 0 ? (
            <p className="text-sm text-muted-foreground px-2">No conversations yet</p>
          ) : (
            conversations.map((conversation) => (
              <Button key={conversation.id} variant={conversation.active ? "secondary" : "ghost"} className={`w-full justify-start text-left truncate ${conversation.active ? "bg-accent" : ""}`} onClick={() => handleSelectConversation(conversation.id)}>
                <MessageSquare className="mr-2 h-4 w-4 shrink-0" />
                <span className="truncate">{conversation.title}</span>
              </Button>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export default ConversationList;
