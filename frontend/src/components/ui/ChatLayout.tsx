import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "@/components/ui/resizable";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { LayoutGrid, MessageCircle, Settings } from "lucide-react";
import React from "react";
import { ThemeToggle } from "./ThemeToggle";

interface ChatLayoutProps {
  sidebar: React.ReactNode;
  mainContent: React.ReactNode;
  settingsPanel: React.ReactNode;
}

const ChatLayout: React.FC<ChatLayoutProps> = ({ sidebar, mainContent, settingsPanel }) => {
  return (
    <div className="h-screen flex flex-col">
      <header className="border-b-2 h-14 flex items-center px-6">
        <h1 className="text-xl font-semibold">KnowledgeNet: Deep Research</h1>
        <div className="flex-1" />
        <ThemeToggle />
        <Sheet>
          <SheetTrigger asChild>
            <Button variant="ghost" size="icon">
              <Settings size={20} />
            </Button>
          </SheetTrigger>
          <SheetContent>
            <div className="py-4">
              <h2 className="text-lg font-semibold mb-4">Research Settings</h2>
              {settingsPanel}
            </div>
          </SheetContent>
        </Sheet>
      </header>

      <div className="flex-1 overflow-hidden">
        <ResizablePanelGroup direction="horizontal">
          <ResizablePanel defaultSize={20} minSize={15} maxSize={30} className="hidden md:block">
            <Card className="h-full rounded-none border-r border-t-0 border-l-0 border-b-0">
              <ScrollArea className="h-full">{sidebar}</ScrollArea>
            </Card>
          </ResizablePanel>

          <ResizableHandle withHandle className="hidden md:flex" />

          <ResizablePanel defaultSize={80}>
            <Tabs defaultValue="chat" className="h-full flex flex-col">
              <div className="p-4">
                <TabsList className="">
                  <TabsTrigger value="chat" className="flex items-center gap-2">
                    <MessageCircle size={16} />
                    <span>Chat</span>
                  </TabsTrigger>
                  <TabsTrigger value="visualizations" className="flex items-center gap-2">
                    <LayoutGrid size={16} />
                    <span>Visualizations</span>
                  </TabsTrigger>
                </TabsList>
              </div>

              <TabsContent value="chat" className="overflow-auto flex flex-1" tabIndex={-1}>
                {mainContent}
              </TabsContent>

              <TabsContent value="visualizations" className="p-4 flex-1">
                <div className="h-full flex items-center justify-center text-muted-foreground">
                  <div className="text-center">
                    <LayoutGrid className="mx-auto h-12 w-12 mb-4 opacity-30" />
                    <h3 className="text-lg font-medium mb-2">Visualizations Coming Soon</h3>
                    <p>View graphs, charts, and other visual representations of your research data.</p>
                  </div>
                </div>
              </TabsContent>
            </Tabs>
          </ResizablePanel>
        </ResizablePanelGroup>
      </div>
    </div>
  );
};

export default ChatLayout;
