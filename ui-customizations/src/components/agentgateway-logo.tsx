import Image from "next/image";

export function AgentgatewayLogo({ className }: { className?: string }) {
  return (
    <Image
      src="/ui/images/unitone-logo.png"
      alt="UnitOne"
      width={36}
      height={36}
      className={className}
    />
  );
}
