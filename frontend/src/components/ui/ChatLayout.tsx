import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "@/components/ui/resizable";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { LayoutGrid, Menu, MessageCircle, Settings } from "lucide-react";
import React from "react";
import { ThemeToggle } from "./ThemeToggle";
import Link from "next/link";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Sheet, SheetContent, SheetTrigger, SheetTitle, SheetDescription } from "@/components/ui/sheet";

interface ChatLayoutProps {
  sidebar: React.ReactNode;
  mainContent: React.ReactNode;
  settingsPanel: React.ReactNode;
}

const ChatLayout: React.FC<ChatLayoutProps> = ({ sidebar, mainContent, settingsPanel }) => {
  return (
    <div className="h-screen flex flex-col">
      <header className="border-b-2 h-14 flex items-center px-6">
        <Sheet>
          <SheetTrigger asChild>
            <Button variant="ghost" size="icon" className="md:hidden mr-2">
              <Menu size={20} />
              <span className="sr-only">Toggle sidebar</span>
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="w-[80%] sm:w-[350px] p-0">
            <SheetTitle className="sr-only">Mobile Navigation</SheetTitle>
            <SheetDescription className="sr-only">Sidebar navigation for mobile devices</SheetDescription>
            <div className="border-b p-4">
              <h2 className="text-lg font-semibold">Conversations</h2>
            </div>
            <ScrollArea className="h-[calc(100%-60px)] py-2">{sidebar}</ScrollArea>
          </SheetContent>
        </Sheet>

        <Link href={"/"}>
          <h1 className="text-xl font-semibold hidden sm:inline">KnowledgeNet: Deep Research</h1>
          <h1 className="text-lg font-semibold sm:hidden">KNet: Deep Research</h1>
        </Link>
        <div className="flex-1" />
        <ThemeToggle />
        <Dialog>
          <DialogTrigger asChild>
            <Button variant="ghost" size="icon" className="h-9 w-9" title="Settings">
              <Settings size={20} />
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Research Settings</DialogTitle>
              <DialogDescription>Configure your research parameters and preferences.</DialogDescription>
            </DialogHeader>
            {settingsPanel}
          </DialogContent>
        </Dialog>
      </header>

      <div className="flex-1 overflow-hidden">
        <ResizablePanelGroup direction="horizontal">
          <ResizablePanel defaultSize={15} className="hidden md:block min-w-[15rem] max-w-[35rem]">
            <Card className="h-full rounded-none border-r border-t-0 border-l-0 border-b-0">
              <ScrollArea className="h-full">{sidebar}</ScrollArea>
            </Card>
          </ResizablePanel>

          <ResizableHandle withHandle className="hidden md:flex" />

          <ResizablePanel defaultSize={85} className="w-full md:w-auto">
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

              <TabsContent value="chat" className="overflow-auto flex flex-1 !mt-0" tabIndex={-1}>
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
