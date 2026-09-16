import { useState } from "react";
import { AlertTriangle, CheckCircle, Loader, Settings, User, LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Toaster, toast } from "@/components/ui/toaster";

export default function SettingsPage() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Mock form state
  const [formState, setFormState] = useState({
    username: "Sarah Chen",
    email: "sarah@example.com",
    notifications: true,
    mlMode: "mock", // or "real"
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    setSuccess(null);

    try {
      // In a real app, we would send this to the backend
      // For now, we'll just simulate a delay and show success
      await new Promise(resolve => setTimeout(resolve, 1000));
      setSuccess("Settings saved successfully!");
      // Optionally, we could update some global state or context
    } catch (err: any) {
      setError(err.message || "Failed to save settings");
      toast.error("Error saving settings: " + err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col items-center justify-center">
        <h2 className="text-2xl font-semibold tracking-[-0.05em]">Settings</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Configure your PlantGuard AI experience
        </p>
      </div>

      {/* Settings Form */}
      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="border border-border/80 rounded-xl p-4">
          <h3 className="text-[16px] font-semibold tracking-[-0.02em]">Account</h3>
          <Form>
            <FormField>
              <FormLabel>Username</FormLabel>
              <FormControl>
                <Input
                  defaultValue={formState.username}
                  onChange={(e) => setFormState({ ...formState, username: e.target.value })}
                  disabled={isLoading}
                />
              </FormControl>
              <FormMessage />
            </FormField>
            <FormField>
              <FormLabel>Email</FormLabel>
              <FormControl>
                <Input
                  type="email"
                  defaultValue={formState.email}
                  onChange={(e) => setFormState({ ...formState, email: e.target.value })}
                  disabled={isLoading}
                />
              </FormControl>
              <FormMessage />
            </FormField>
          </Form>
        </div>

        <div className="border border-border/80 rounded-xl p-4">
          <h3 className="text-[16px] font-semibold tracking-[-0.02em]">Preferences</h3>
          <Form>
            <FormField>
              <FormLabel>Notifications</FormLabel>
              <FormControl>
                <label className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    checked={formState.notifications}
                    onChange={(e) => setFormState({ ...formState, notifications: e.target.checked })}
                    disabled={isLoading}
                    className="h-4 w-4 rounded border-primary focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                  <span>Enable notifications</span>
                </label>
              </FormControl>
              <FormMessage />
            </FormField>
            <FormField>
              <FormLabel>ML Model Mode</FormLabel>
              <FormControl>
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2">
                    <input
                      type="radio"
                      name="mlMode"
                      value="mock"
                      checked={formState.mlMode === "mock"}
                      onChange={(e) => setFormState({ ...formState, mlMode: e.target.value })}
                      disabled={isLoading}
                      className="h-4 w-4 rounded border-primary focus:outline-none focus:ring-2 focus:ring-primary"
                    />
                    <span>Mock (for development)</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <input
                      type="radio"
                      name="mlMode"
                      value="real"
                      checked={formState.mlMode === "real"}
                      onChange={(e) => setFormState({ ...formState, mlMode: e.target.value })}
                      disabled={isLoading}
                      className="h-4 w-4 rounded border-primary focus:outline-none focus:ring-2 focus:ring-primary"
                    />
                    <span>Real (production models)</span>
                  </div>
                </div>
              </FormControl>
              <FormMessage />
            </FormField>
          </Form>
        </div>

        <div className="border border-border/80 rounded-xl p-4">
          <h3 className="text-[16px] font-semibold tracking-[-0.02em]">Actions</h3>
          <div className="space-y-3">
            <Button
              variant="outline"
              onClick={() => toast.info("Logout functionality would clear session and redirect to login")}
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <Loader size={16} className="mr-2" />
                  Processing...
                </>
              ) : (
                <>
                  <LogOut size={16} className="mr-2" />
                  Log Out
                </>
              )}
            </Button>
            <Button
              variant="destructive"
              onClick={() => {
                // In a real app, we would confirm and then delete account data
                toast.warning("Account deletion not yet implemented");
              }}
              disabled={isLoading}
            >
              Delete Account
            </Button>
          </div>
        </div>
      </form>

      {/* Status Messages */}
      {error && (
        <div className="rounded-xl border border-destructive/50 bg-destructive/50 p-4">
          <AlertTriangle size={20} className="mr-3 h-4 w-4 text-destructive" />
          <span>{error}</span>
        </div>
      )}
      {success && (
        <div className="rounded-xl border border-success/50 bg-success/50 p-4">
          <CheckCircle size={20} className="mr-3 h-4 w-4 text-success" />
          <span>{success}</span>
        </div>
      )}
    </div>
  );
}