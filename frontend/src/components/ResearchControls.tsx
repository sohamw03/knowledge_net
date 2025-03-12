import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { ResearchOptions } from "@/lib/types";
import React from "react";

interface ResearchControlsProps {
  options: ResearchOptions;
  onOptionChange: (options: ResearchOptions) => void;
}

const ResearchControls: React.FC<ResearchControlsProps> = ({ options, onOptionChange }) => {
  return (
    <div className="space-y-6">
      <div className="space-y-3">
        <Label htmlFor="research-depth">Research Depth</Label>
        <Select value={options.depth} onValueChange={(value: ResearchOptions["depth"]) => onOptionChange({ ...options, depth: value })}>
          <SelectTrigger id="research-depth" className="w-full">
            <SelectValue placeholder="Select depth" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="basic">Basic</SelectItem>
            <SelectItem value="intermediate">Intermediate</SelectItem>
            <SelectItem value="deep">Deep</SelectItem>
          </SelectContent>
        </Select>
        <p className="text-xs text-muted-foreground">Determines how extensively the assistant will research your query.</p>
      </div>

      <Separator />

      <div className="space-y-3">
        <Label>Inclusions</Label>

        <div className="flex items-center space-x-2">
          <Checkbox id="sources" checked={options.sources} onCheckedChange={(checked) => onOptionChange({ ...options, sources: checked as boolean })} />
          <Label htmlFor="sources" className="text-sm font-normal">
            Include sources
          </Label>
        </div>

        <div className="flex items-center space-x-2">
          <Checkbox id="citations" checked={options.citations} onCheckedChange={(checked) => onOptionChange({ ...options, citations: checked as boolean })} />
          <Label htmlFor="citations" className="text-sm font-normal">
            Include citations
          </Label>
        </div>
      </div>

      <Separator />

      <div className="space-y-3">
        <Label>Coming Soon</Label>
        <div className="flex items-center space-x-2">
          <Checkbox id="visualize" disabled />
          <Label htmlFor="visualize" className="text-sm font-normal text-muted-foreground">
            Generate visualizations
          </Label>
        </div>

        <div className="flex items-center space-x-2">
          <Checkbox id="video-content" disabled />
          <Label htmlFor="video-content" className="text-sm font-normal text-muted-foreground">
            Include video content
          </Label>
        </div>
      </div>
    </div>
  );
};

export default ResearchControls;
