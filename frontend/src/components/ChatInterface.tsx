"use client";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { useChatContext } from "@/lib/store/ChatContext";
import React from "react";
import ChatHistory from "./ChatHistory";
import MessageInput from "./MessageInput";
import ResearchControls from "./ResearchControls";
import ChatLayout from "./ui/ChatLayout";
import ConversationList from "./ui/ConversationList";

const ChatInterface = () => {
  const { chatState, conversations, abortResearch, userInputRef, researchOptions, sendMessage, newConversation, selectConversation, deleteConversation, deleteAllConversations, setResearchOptions } = useChatContext();

  const sidebar = <ConversationList conversations={conversations} onNewConversation={newConversation} onSelectConversation={selectConversation} onDeleteConversation={deleteConversation} onDeleteAllConversations={deleteAllConversations} />;

  const mainContent = (
    <div className="flex flex-col w-full h-full relative" tabIndex={-1}>
      <ChatHistory messages={chatState.messages} isLoading={chatState.isLoading} />

      {chatState.error && (
        <Alert variant="destructive" className="mx-2 my-2 mb-28 w-90 bg-red-950 text-red-50">
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{chatState.error}</AlertDescription>
        </Alert>
      )}

      <MessageInput onSendMessage={sendMessage} isLoading={chatState.isLoading} userInputRef={userInputRef} onCancel={abortResearch} />
    </div>
  );

  return <ChatLayout sidebar={sidebar} mainContent={mainContent} settingsPanel={<ResearchControls options={researchOptions} onOptionChange={setResearchOptions} />} />;
};

export default ChatInterface;
