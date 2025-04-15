"use client";
import { Button } from "@/components/ui/button";
import { useChatContext } from "@/lib/store/ChatContext";
import { MessageSquare, PlusCircle, Trash2, XCircle } from "lucide-react";
import React from "react";

interface ConversationListProps {
  conversations: any[];
  onNewConversation: () => void;
  onSelectConversation: (id: string) => void;
  onDeleteConversation: (id: string) => void;
  onDeleteAllConversations: () => void;
}

// A component that accepts props for backward compatibility
const ConversationList: React.FC<ConversationListProps> = ({ conversations, onNewConversation, onSelectConversation, onDeleteConversation, onDeleteAllConversations }) => {
  const handleSelectConversation = (id: string) => {
    onSelectConversation(id);
  };

  return (
    <div className="flex flex-col h-full py-2">
      <div className="px-4 py-2 flex gap-2">
        <Button onClick={onNewConversation} className="flex-1 justify-start" variant="outline">
          <PlusCircle className="mr-2 h-4 w-4" />
          New Chat
        </Button>
        {conversations.length > 0 && (
          <Button onClick={onDeleteAllConversations} variant="destructive" size="icon">
            <Trash2 className="h-4 w-4" />
          </Button>
        )}
      </div>
      <div className="px-2 py-2">
        <h2 className="text-sm font-semibold px-2 mb-2">Recent Research</h2>
        <div className="space-y-1">
          {conversations.length === 0 ? (
            <p className="text-sm text-muted-foreground px-2">No conversations yet</p>
          ) : (
            conversations.map((conversation) => (
              <div key={conversation.id} className="flex items-center gap-1 px-1 group">
                <Button variant={conversation.active ? "secondary" : "ghost"} className={`flex-1 pr-0.5 justify-start text-left truncate ${conversation.active ? "bg-accent" : ""}`} onClick={() => handleSelectConversation(conversation.id)}>
                  <MessageSquare className="mr-2 h-4 w-4 shrink-0" />
                  <span className="truncate">{conversation.title}</span>
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 ml-auto hidden group-hover:flex hover:bg-destructive"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteConversation(conversation.id);
                  }}>
                  <XCircle className="h-4 w-4" />
                </Button>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

// A component that uses context directly
export const ConversationListWithContext: React.FC = () => {
  const { conversations, newConversation, selectConversation, deleteConversation, deleteAllConversations } = useChatContext();

  return <ConversationList conversations={conversations} onNewConversation={newConversation} onSelectConversation={selectConversation} onDeleteConversation={deleteConversation} onDeleteAllConversations={deleteAllConversations} />;
};

export default ConversationList;
