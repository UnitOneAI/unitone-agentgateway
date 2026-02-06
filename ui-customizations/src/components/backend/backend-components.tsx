"use client";

import React from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Plus,
  Target,
  ChevronDown,
  ChevronRight,
  Trash2,
  Edit,
  Brain,
  Cloud,
  Server,
  Globe,
  Loader2,
  Shield,
  AlertTriangle,
} from "lucide-react";
import { Bind, SecurityGuard } from "@/lib/types";
import { BackendWithContext } from "@/lib/backend-hooks";
import {
  DEFAULT_BACKEND_FORM,
  BACKEND_TYPES,
  BACKEND_TABLE_HEADERS,
  HOST_TYPES,
  AI_MODEL_PLACEHOLDERS,
  AI_REGION_PLACEHOLDERS,
  SECURITY_GUARD_TYPES,
  GUARD_PHASES,
  FAILURE_MODES,
  PII_TYPES,
  PII_ACTIONS,
  SCAN_FIELDS,
  getDefaultGuard,
} from "@/lib/backend-constants";
import {
  getBackendType,
  getBackendName,
  getBackendTypeColor,
  getBackendDetails,
  getAvailableRoutes,
  AI_PROVIDERS,
  MCP_TARGET_TYPES,
  hasBackendPolicies,
  getBackendPolicyTypes,
  canDeleteBackend,
} from "@/lib/backend-utils";
import { useXdsMode } from "@/hooks/use-xds-mode";

const getEnvAsRecord = (env: unknown): Record<string, string> => {
  return typeof env === "object" && env !== null ? (env as Record<string, string>) : {};
};

// Icon mapping
const getBackendIcon = (type: string) => {
  switch (type) {
    case "mcp":
      return <Target className="h-4 w-4" />;
    case "ai":
      return <Brain className="h-4 w-4" />;
    case "service":
      return <Cloud className="h-4 w-4" />;
    case "host":
      return <Server className="h-4 w-4" />;
    case "dynamic":
      return <Globe className="h-4 w-4" />;
    default:
      return <Server className="h-4 w-4" />;
  }
};

interface BackendTableProps {
  backendsByBind: Map<number, BackendWithContext[]>;
  expandedBinds: Set<number>;
  setExpandedBinds: React.Dispatch<React.SetStateAction<Set<number>>>;
  onEditBackend: (backendContext: BackendWithContext) => void;
  onDeleteBackend: (backendContext: BackendWithContext) => void;
  isSubmitting: boolean;
}

export const BackendTable: React.FC<BackendTableProps> = ({
  backendsByBind,
  expandedBinds,
  setExpandedBinds,
  onEditBackend,
  onDeleteBackend,
  isSubmitting,
}) => {
  const xds = useXdsMode();
  return (
    <div className="space-y-4">
      {Array.from(backendsByBind.entries()).map(([port, backendContexts]) => {
        const typeCounts = backendContexts.reduce(
          (acc, bc) => {
            const type = getBackendType(bc.backend);
            acc[type] = (acc[type] || 0) + 1;
            return acc;
          },
          {} as Record<string, number>
        );

        return (
          <Card key={port}>
            <Collapsible
              open={expandedBinds.has(port)}
              onOpenChange={() => {
                setExpandedBinds((prev) => {
                  const newSet = new Set(prev);
                  if (newSet.has(port)) {
                    newSet.delete(port);
                  } else {
                    newSet.add(port);
                  }
                  return newSet;
                });
              }}
            >
              <CollapsibleTrigger asChild>
                <CardHeader className="hover:bg-muted/50 cursor-pointer">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4">
                      {expandedBinds.has(port) ? (
                        <ChevronDown className="h-4 w-4" />
                      ) : (
                        <ChevronRight className="h-4 w-4" />
                      )}
                      <div>
                        <h3 className="text-lg font-semibold">Port {port}</h3>
                        <div className="flex items-center space-x-4 text-sm text-muted-foreground mt-1">
                          {Object.entries(typeCounts).map(([type, count]) => (
                            <div key={type} className="flex items-center space-x-1">
                              {getBackendIcon(type)}
                              <span>
                                {count} {type.toUpperCase()}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                    <Badge>{backendContexts.length} backends</Badge>
                  </div>
                </CardHeader>
              </CollapsibleTrigger>

              <CollapsibleContent>
                <CardContent className="pt-0">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        {BACKEND_TABLE_HEADERS.map((header) => (
                          <TableHead
                            key={header}
                            className={header === "Actions" ? "text-right" : ""}
                          >
                            {header}
                          </TableHead>
                        ))}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {backendContexts.map((backendContext, index) => {
                        const type = getBackendType(backendContext.backend);
                        return (
                          <TableRow key={index}>
                            <TableCell className="font-medium">
                              {getBackendName(backendContext.backend)}
                            </TableCell>
                            <TableCell>
                              <Badge
                                variant="secondary"
                                className={`${getBackendTypeColor(type)} text-white`}
                              >
                                {getBackendIcon(type)}
                                <span className="ml-1 capitalize">{type}</span>
                              </Badge>
                            </TableCell>
                            <TableCell>
                              <Badge variant="outline">
                                {backendContext.listener.name || "unnamed"}
                              </Badge>
                            </TableCell>
                            <TableCell>
                              <Badge variant="outline">
                                {backendContext.route.name ||
                                  `Route ${backendContext.routeIndex + 1}`}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-sm text-muted-foreground">
                              {(() => {
                                const details = getBackendDetails(backendContext.backend);
                                const hasPolicies = hasBackendPolicies(backendContext.route);
                                const policyTypes = hasPolicies
                                  ? getBackendPolicyTypes(backendContext.route)
                                  : [];

                                return (
                                  <div className="space-y-1">
                                    <div>{details.primary}</div>
                                    {details.secondary && (
                                      <div className="text-xs text-muted-foreground/80 font-mono">
                                        {details.secondary}
                                      </div>
                                    )}
                                    {hasPolicies && (
                                      <div className="flex items-center space-x-1 mt-1">
                                        <Shield className="h-3 w-3 text-primary" />
                                        <span className="text-xs text-primary font-medium">
                                          Backend Policies: {policyTypes.join(", ")}
                                        </span>
                                      </div>
                                    )}
                                  </div>
                                );
                              })()}
                            </TableCell>
                            <TableCell>
                              <Badge>{backendContext.backend.weight || 1}</Badge>
                            </TableCell>
                            <TableCell className="text-right">
                              <div className="flex justify-end space-x-2">
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  onClick={() => onEditBackend(backendContext)}
                                  disabled={xds}
                                  className={xds ? "opacity-50 cursor-not-allowed" : undefined}
                                >
                                  <Edit className="h-4 w-4" />
                                </Button>
                                {(() => {
                                  const totalBackendsInRoute = backendContexts.filter(
                                    (bc) =>
                                      bc.bind.port === backendContext.bind.port &&
                                      bc.listener.name === backendContext.listener.name &&
                                      bc.routeIndex === backendContext.routeIndex
                                  ).length;

                                  const deleteCheck = canDeleteBackend(
                                    backendContext.route,
                                    totalBackendsInRoute
                                  );

                                  if (!deleteCheck.canDelete) {
                                    return (
                                      <TooltipProvider>
                                        <Tooltip>
                                          <TooltipTrigger asChild>
                                            <div>
                                              <Button
                                                variant="ghost"
                                                size="icon"
                                                disabled={true}
                                                className="text-muted-foreground cursor-not-allowed"
                                              >
                                                <div className="relative">
                                                  <Trash2 className="h-4 w-4" />
                                                  <AlertTriangle className="h-2 w-2 absolute -top-0.5 -right-0.5 text-amber-500" />
                                                </div>
                                              </Button>
                                            </div>
                                          </TooltipTrigger>
                                          <TooltipContent className="max-w-sm">
                                            <p>{deleteCheck.reason}</p>
                                          </TooltipContent>
                                        </Tooltip>
                                      </TooltipProvider>
                                    );
                                  }

                                  return (
                                    <Button
                                      variant="ghost"
                                      size="icon"
                                      onClick={() => onDeleteBackend(backendContext)}
                                      className={`text-destructive hover:text-destructive ${xds ? "opacity-50 cursor-not-allowed" : ""}`}
                                      disabled={isSubmitting || xds}
                                    >
                                      <Trash2 className="h-4 w-4" />
                                    </Button>
                                  );
                                })()}
                              </div>
                            </TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                </CardContent>
              </CollapsibleContent>
            </Collapsible>
          </Card>
        );
      })}
    </div>
  );
};

interface AddBackendDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  binds: Bind[];
  backendForm: typeof DEFAULT_BACKEND_FORM;
  setBackendForm: React.Dispatch<React.SetStateAction<typeof DEFAULT_BACKEND_FORM>>;
  selectedBackendType: string;
  setSelectedBackendType: React.Dispatch<React.SetStateAction<string>>;
  editingBackend: BackendWithContext | null;
  onAddBackend: () => void;
  onCancel: () => void;
  isSubmitting: boolean;
  addMcpTarget: () => void;
  removeMcpTarget: (index: number) => void;
  updateMcpTarget: (index: number, field: string, value: any) => void;
  parseAndUpdateUrl: (index: number, url: string) => void;
  updateMcpStateful: (stateful: boolean) => void;
}

export const AddBackendDialog: React.FC<AddBackendDialogProps> = ({
  open,
  onOpenChange,
  binds,
  backendForm,
  setBackendForm,
  selectedBackendType,
  setSelectedBackendType,
  editingBackend,
  onAddBackend,
  onCancel,
  isSubmitting,
  addMcpTarget,
  removeMcpTarget,
  updateMcpTarget,
  parseAndUpdateUrl,
  updateMcpStateful,
}) => {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {editingBackend
              ? `Edit Backend: ${getBackendName(editingBackend.backend)}`
              : `Add ${selectedBackendType.toUpperCase()} Backend`}
          </DialogTitle>
          <DialogDescription>
            {editingBackend
              ? "Update the backend configuration."
              : "Configure a new backend for your routes."}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label>Backend Type *</Label>
            <div className="grid grid-cols-2 gap-2">
              {BACKEND_TYPES.map(({ value, label, icon }) => {
                const IconComponent = { Target, Brain, Cloud, Server, Globe }[icon];
                return (
                  <Button
                    key={value}
                    type="button"
                    variant={selectedBackendType === value ? "default" : "outline"}
                    onClick={() => setSelectedBackendType(value)}
                    className="justify-start"
                  >
                    <IconComponent className="mr-2 h-4 w-4" />
                    {label}
                  </Button>
                );
              })}
            </div>
          </div>

          <div className={selectedBackendType === "ai" || selectedBackendType === "mcp" ? "space-y-4" : "grid grid-cols-2 gap-4"}>
            {selectedBackendType !== "mcp" && (
              <div className="space-y-2">
                <Label htmlFor="backend-name">Name *</Label>
                <Input
                  id="backend-name"
                  value={backendForm.name}
                  onChange={(e) => setBackendForm((prev) => ({ ...prev, name: e.target.value }))}
                  placeholder="Backend name"
                />
              </div>
            )}
            <div className="space-y-2">
              <Label htmlFor="backend-weight">Weight</Label>
              <Input
                id="backend-weight"
                type="number"
                min="0"
                step="1"
                value={backendForm.weight}
                onChange={(e) => setBackendForm((prev) => ({ ...prev, weight: e.target.value }))}
                placeholder="1"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label>Route *</Label>
            {editingBackend ? (
              <div className="p-3 bg-muted rounded-md">
                <p className="text-sm">
                  Port {editingBackend.bind.port} → {editingBackend.listener.name || "unnamed"} →{" "}
                  {editingBackend.route.name || `Route ${editingBackend.routeIndex + 1}`}
                </p>
              </div>
            ) : (
              <Select
                value={`${backendForm.selectedBindPort}-${backendForm.selectedListenerName}-${backendForm.selectedRouteIndex}`}
                onValueChange={(value) => {
                  const [bindPort, listenerName, routeIndex] = value.split("-");
                  setBackendForm((prev) => ({
                    ...prev,
                    selectedBindPort: bindPort,
                    selectedListenerName: listenerName,
                    selectedRouteIndex: routeIndex,
                  }));
                }}
              >
                <SelectTrigger><SelectValue placeholder="Select a route" /></SelectTrigger>
                <SelectContent>
                  {getAvailableRoutes(binds).map((route) => (
                    <SelectItem
                      key={`${route.bindPort}-${route.listenerName}-${route.routeIndex}`}
                      value={`${route.bindPort}-${route.listenerName}-${route.routeIndex}`}
                    >
                      Port {route.bindPort} → {route.listenerName} → {route.routeName} ({route.path})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>

          {selectedBackendType === "service" && <ServiceBackendForm backendForm={backendForm} setBackendForm={setBackendForm} />}
          {selectedBackendType === "host" && <HostBackendForm backendForm={backendForm} setBackendForm={setBackendForm} />}
          {selectedBackendType === "mcp" && (
            <McpBackendForm
              backendForm={backendForm}
              setBackendForm={setBackendForm}
              addMcpTarget={addMcpTarget}
              removeMcpTarget={removeMcpTarget}
              updateMcpTarget={updateMcpTarget}
              parseAndUpdateUrl={parseAndUpdateUrl}
              updateMcpStateful={updateMcpStateful}
            />
          )}
          {selectedBackendType === "ai" && <AiBackendForm backendForm={backendForm} setBackendForm={setBackendForm} />}
          {selectedBackendType === "dynamic" && (
            <div className="p-4 bg-muted/50 rounded-lg">
              <p className="text-sm text-muted-foreground">Dynamic backends are automatically configured.</p>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onCancel}>Cancel</Button>
          <Button onClick={onAddBackend} disabled={isSubmitting}>
            {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {editingBackend ? "Update" : "Add"} Backend
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

const ServiceBackendForm: React.FC<{ backendForm: typeof DEFAULT_BACKEND_FORM; setBackendForm: React.Dispatch<React.SetStateAction<typeof DEFAULT_BACKEND_FORM>> }> = ({ backendForm, setBackendForm }) => (
  <div className="space-y-4">
    <div className="grid grid-cols-2 gap-4">
      <div className="space-y-2">
        <Label>Namespace *</Label>
        <Input value={backendForm.serviceNamespace} onChange={(e) => setBackendForm((prev) => ({ ...prev, serviceNamespace: e.target.value }))} placeholder="default" />
      </div>
      <div className="space-y-2">
        <Label>Hostname *</Label>
        <Input value={backendForm.serviceHostname} onChange={(e) => setBackendForm((prev) => ({ ...prev, serviceHostname: e.target.value }))} placeholder="my-service" />
      </div>
    </div>
    <div className="space-y-2">
      <Label>Port *</Label>
      <Input type="number" value={backendForm.servicePort} onChange={(e) => setBackendForm((prev) => ({ ...prev, servicePort: e.target.value }))} placeholder="80" />
    </div>
  </div>
);

const HostBackendForm: React.FC<{ backendForm: typeof DEFAULT_BACKEND_FORM; setBackendForm: React.Dispatch<React.SetStateAction<typeof DEFAULT_BACKEND_FORM>> }> = ({ backendForm, setBackendForm }) => (
  <div className="space-y-4">
    <div className="flex space-x-4">
      {HOST_TYPES.map(({ value, label }) => (
        <Button key={value} type="button" variant={backendForm.hostType === value ? "default" : "outline"} onClick={() => setBackendForm((prev) => ({ ...prev, hostType: value as any }))}>{label}</Button>
      ))}
    </div>
    {backendForm.hostType === "address" ? (
      <Input value={backendForm.hostAddress} onChange={(e) => setBackendForm((prev) => ({ ...prev, hostAddress: e.target.value }))} placeholder="192.168.1.100:8080" />
    ) : (
      <div className="grid grid-cols-2 gap-4">
        <Input value={backendForm.hostHostname} onChange={(e) => setBackendForm((prev) => ({ ...prev, hostHostname: e.target.value }))} placeholder="example.com" />
        <Input type="number" value={backendForm.hostPort} onChange={(e) => setBackendForm((prev) => ({ ...prev, hostPort: e.target.value }))} placeholder="8080" />
      </div>
    )}
  </div>
);

const McpBackendForm: React.FC<{
  backendForm: typeof DEFAULT_BACKEND_FORM;
  setBackendForm: React.Dispatch<React.SetStateAction<typeof DEFAULT_BACKEND_FORM>>;
  addMcpTarget: () => void;
  removeMcpTarget: (index: number) => void;
  updateMcpTarget: (index: number, field: string, value: any) => void;
  parseAndUpdateUrl: (index: number, url: string) => void;
  updateMcpStateful: (stateful: boolean) => void;
}> = ({ backendForm, setBackendForm, addMcpTarget, removeMcpTarget, updateMcpTarget, parseAndUpdateUrl, updateMcpStateful }) => {
  const addSecurityGuard = (type: SecurityGuard["type"]) => {
    const newGuard = getDefaultGuard(type);
    setBackendForm((prev) => ({ ...prev, securityGuards: [...prev.securityGuards, newGuard] }));
  };

  const removeSecurityGuard = (index: number) => {
    setBackendForm((prev) => ({ ...prev, securityGuards: prev.securityGuards.filter((_, i) => i !== index) }));
  };

  const updateSecurityGuard = (index: number, field: string, value: any) => {
    setBackendForm((prev) => ({
      ...prev,
      securityGuards: prev.securityGuards.map((guard, i) => i === index ? { ...guard, [field]: value } : guard),
    }));
  };

  return (
    <div className="space-y-6">
      {/* MCP Targets */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <Label>MCP Targets</Label>
          <Button type="button" variant="outline" size="sm" onClick={addMcpTarget}><Plus className="mr-1 h-3 w-3" />Add Target</Button>
        </div>

        {backendForm.mcpTargets.map((target, index) => (
          <Card key={index} className="p-4">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h4 className="text-sm font-medium">Target {index + 1}</h4>
                <Button type="button" variant="ghost" size="sm" onClick={() => removeMcpTarget(index)} className="text-destructive"><Trash2 className="h-3 w-3" /></Button>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Name *</Label>
                  <Input value={target.name} onChange={(e) => updateMcpTarget(index, "name", e.target.value)} placeholder="my-target" />
                </div>
                <div className="space-y-2">
                  <Label>Type *</Label>
                  <Select value={target.type} onValueChange={(value) => updateMcpTarget(index, "type", value)}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {MCP_TARGET_TYPES.map(({ value, label }) => (<SelectItem key={value} value={value}>{label}</SelectItem>))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              {(target.type === "sse" || target.type === "mcp" || target.type === "openapi") && (
                <div className="space-y-2">
                  <Label>URL *</Label>
                  <Input value={target.fullUrl} onChange={(e) => parseAndUpdateUrl(index, e.target.value)} placeholder="https://example.com/mcp" />
                </div>
              )}
              {target.type === "stdio" && (
                <div className="space-y-2">
                  <Label>Command *</Label>
                  <Input value={target.cmd} onChange={(e) => updateMcpTarget(index, "cmd", e.target.value)} placeholder="python3 server.py" />
                </div>
              )}
            </div>
          </Card>
        ))}

        {backendForm.mcpTargets.length === 0 && (
          <div className="text-center py-8 border-2 border-dashed rounded-md">
            <Target className="mx-auto h-8 w-8 text-muted-foreground mb-2" />
            <p className="text-sm text-muted-foreground">No targets configured</p>
          </div>
        )}

        <div className="flex items-center space-x-2">
          <input type="checkbox" id="mcp-stateful" checked={!!backendForm.mcpStateful} onChange={(e) => updateMcpStateful(e.target.checked)} className="h-4 w-4" />
          <Label htmlFor="mcp-stateful">Enable stateful mode</Label>
        </div>
      </div>

      {/* Security Guards */}
      <div className="space-y-4 border-t pt-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Shield className="h-4 w-4 text-primary" />
            <Label className="text-base font-semibold">Security Guards</Label>
          </div>
          <Select onValueChange={(value) => addSecurityGuard(value as SecurityGuard["type"])}>
            <SelectTrigger className="w-[180px]"><SelectValue placeholder="Add guard..." /></SelectTrigger>
            <SelectContent>
              {SECURITY_GUARD_TYPES.map(({ value, label }) => (<SelectItem key={value} value={value}>{label}</SelectItem>))}
            </SelectContent>
          </Select>
        </div>

        {backendForm.securityGuards.length === 0 ? (
          <div className="text-center py-6 border-2 border-dashed rounded-md">
            <Shield className="mx-auto h-8 w-8 text-muted-foreground mb-2" />
            <p className="text-sm text-muted-foreground">No security guards configured</p>
          </div>
        ) : (
          <div className="space-y-3">
            {backendForm.securityGuards.map((guard, index) => (
              <Card key={guard.id || index} className="p-4">
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <Badge variant="secondary">{SECURITY_GUARD_TYPES.find((t) => t.value === guard.type)?.label || guard.type}</Badge>
                      <input type="checkbox" checked={guard.enabled !== false} onChange={(e) => updateSecurityGuard(index, "enabled", e.target.checked)} className="h-4 w-4" />
                      <span className="text-xs text-muted-foreground">Enabled</span>
                    </div>
                    <Button type="button" variant="ghost" size="sm" onClick={() => removeSecurityGuard(index)} className="text-destructive"><Trash2 className="h-3 w-3" /></Button>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1">
                      <Label className="text-xs">Guard ID</Label>
                      <Input value={guard.id} onChange={(e) => updateSecurityGuard(index, "id", e.target.value)} placeholder="unique-id" className="h-8 text-sm" />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">Priority</Label>
                      <Input type="number" value={guard.priority} onChange={(e) => updateSecurityGuard(index, "priority", parseInt(e.target.value) || 100)} className="h-8 text-sm" />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1">
                      <Label className="text-xs">Failure Mode</Label>
                      <Select value={guard.failure_mode} onValueChange={(value) => updateSecurityGuard(index, "failure_mode", value)}>
                        <SelectTrigger className="h-8 text-sm"><SelectValue /></SelectTrigger>
                        <SelectContent>
                          {FAILURE_MODES.map(({ value, label }) => (<SelectItem key={value} value={value}>{label}</SelectItem>))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">Timeout (ms)</Label>
                      <Input type="number" value={guard.timeout_ms} onChange={(e) => updateSecurityGuard(index, "timeout_ms", parseInt(e.target.value) || 100)} className="h-8 text-sm" />
                    </div>
                  </div>

                  <div className="space-y-1">
                    <Label className="text-xs">Runs On</Label>
                    <div className="flex flex-wrap gap-2">
                      {GUARD_PHASES.map(({ value, label }) => (
                        <label key={value} className="flex items-center space-x-1 text-xs">
                          <input
                            type="checkbox"
                            checked={guard.runs_on?.includes(value) || false}
                            onChange={(e) => {
                              const current = guard.runs_on || [];
                              const newPhases = e.target.checked ? [...current, value] : current.filter((p) => p !== value);
                              updateSecurityGuard(index, "runs_on", newPhases);
                            }}
                            className="h-3 w-3"
                          />
                          <span>{label}</span>
                        </label>
                      ))}
                    </div>
                  </div>

                  {/* Type-specific fields */}
                  {guard.type === "pii" && (
                    <div className="space-y-3 border-t pt-3">
                      <div className="space-y-1">
                        <Label className="text-xs">Detect PII Types</Label>
                        <div className="flex flex-wrap gap-2">
                          {PII_TYPES.map(({ value, label }) => (
                            <label key={value} className="flex items-center space-x-1 text-xs">
                              <input type="checkbox" checked={(guard as any).detect?.includes(value) || false} onChange={(e) => {
                                const current = (guard as any).detect || [];
                                updateSecurityGuard(index, "detect", e.target.checked ? [...current, value] : current.filter((v: string) => v !== value));
                              }} className="h-3 w-3" />
                              <span>{label}</span>
                            </label>
                          ))}
                        </div>
                      </div>
                      <div className="grid grid-cols-2 gap-3">
                        <div className="space-y-1">
                          <Label className="text-xs">Action</Label>
                          <Select value={(guard as any).action || "mask"} onValueChange={(value) => updateSecurityGuard(index, "action", value)}>
                            <SelectTrigger className="h-8 text-sm"><SelectValue /></SelectTrigger>
                            <SelectContent>{PII_ACTIONS.map(({ value, label }) => (<SelectItem key={value} value={value}>{label}</SelectItem>))}</SelectContent>
                          </Select>
                        </div>
                        <div className="space-y-1">
                          <Label className="text-xs">Min Score</Label>
                          <Input type="number" step="0.1" min="0" max="1" value={(guard as any).min_score || 0.3} onChange={(e) => updateSecurityGuard(index, "min_score", parseFloat(e.target.value))} className="h-8 text-sm" />
                        </div>
                      </div>
                    </div>
                  )}

                  {guard.type === "tool_poisoning" && (
                    <div className="space-y-3 border-t pt-3">
                      <div className="flex items-center space-x-2">
                        <input type="checkbox" checked={(guard as any).strict_mode !== false} onChange={(e) => updateSecurityGuard(index, "strict_mode", e.target.checked)} className="h-4 w-4" />
                        <Label className="text-xs">Strict Mode</Label>
                      </div>
                      <div className="space-y-1">
                        <Label className="text-xs">Scan Fields</Label>
                        <div className="flex flex-wrap gap-2">
                          {SCAN_FIELDS.map(({ value, label }) => (
                            <label key={value} className="flex items-center space-x-1 text-xs">
                              <input type="checkbox" checked={(guard as any).scan_fields?.includes(value) || false} onChange={(e) => {
                                const current = (guard as any).scan_fields || [];
                                updateSecurityGuard(index, "scan_fields", e.target.checked ? [...current, value] : current.filter((v: string) => v !== value));
                              }} className="h-3 w-3" />
                              <span>{label}</span>
                            </label>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}

                  {guard.type === "server_whitelist" && (
                    <div className="space-y-3 border-t pt-3">
                      <div className="space-y-1">
                        <Label className="text-xs">Allowed Servers (comma-separated)</Label>
                        <Input value={((guard as any).allowed_servers || []).join(", ")} onChange={(e) => updateSecurityGuard(index, "allowed_servers", e.target.value.split(",").map((s) => s.trim()).filter(Boolean))} placeholder="github.com, slack.com" className="h-8 text-sm" />
                      </div>
                    </div>
                  )}
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

const AiBackendForm: React.FC<{ backendForm: typeof DEFAULT_BACKEND_FORM; setBackendForm: React.Dispatch<React.SetStateAction<typeof DEFAULT_BACKEND_FORM>> }> = ({ backendForm, setBackendForm }) => (
  <div className="space-y-4">
    <div className="grid grid-cols-3 gap-2">
      {AI_PROVIDERS.map(({ value, label }) => (
        <Button key={value} type="button" variant={backendForm.aiProvider === value ? "default" : "outline"} onClick={() => setBackendForm((prev) => ({ ...prev, aiProvider: value as any }))} className="text-sm">{label}</Button>
      ))}
    </div>
    <div className="grid grid-cols-2 gap-4">
      <div className="space-y-2">
        <Label>Model</Label>
        <Input value={backendForm.aiModel} onChange={(e) => setBackendForm((prev) => ({ ...prev, aiModel: e.target.value }))} placeholder={AI_MODEL_PLACEHOLDERS[backendForm.aiProvider]} />
      </div>
      {(backendForm.aiProvider === "vertex" || backendForm.aiProvider === "bedrock") && (
        <div className="space-y-2">
          <Label>Region</Label>
          <Input value={backendForm.aiRegion} onChange={(e) => setBackendForm((prev) => ({ ...prev, aiRegion: e.target.value }))} placeholder={AI_REGION_PLACEHOLDERS[backendForm.aiProvider]} />
        </div>
      )}
    </div>
    {backendForm.aiProvider === "vertex" && (
      <div className="space-y-2">
        <Label>Project ID *</Label>
        <Input value={backendForm.aiProjectId} onChange={(e) => setBackendForm((prev) => ({ ...prev, aiProjectId: e.target.value }))} placeholder="my-gcp-project" />
      </div>
    )}
    {backendForm.aiProvider === "azureOpenAI" && (
      <div className="space-y-2">
        <Label>Host *</Label>
        <Input value={backendForm.aiHost} onChange={(e) => setBackendForm((prev) => ({ ...prev, aiHost: e.target.value }))} placeholder="my-resource.openai.azure.com" />
      </div>
    )}
  </div>
);
