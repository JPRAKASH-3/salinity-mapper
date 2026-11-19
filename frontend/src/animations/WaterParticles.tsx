import { Canvas, useFrame } from "@react-three/fiber"; import { useMemo, useRef } from "react"; import * as THREE from "three";
function Points() {
  const ref = useRef<THREE.Points>(null);
  const pos = useMemo(() => { const a = new Float32Array(900 * 3); for (let i = 0; i < a.length; i++) a[i] = (Math.random() - .5) * 12; return a; }, []);
  useFrame(({ clock }) => { if (ref.current) { ref.current.rotation.y = clock.elapsedTime * .03; ref.current.position.y = Math.sin(clock.elapsedTime * .4) * .2; } });
  return <points ref={ref}><bufferGeometry><bufferAttribute attach="attributes-position" count={900} array={pos} itemSize={3} /></bufferGeometry>
    <pointsMaterial size={.05} color="#38BDF8" transparent opacity={.7} sizeAttenuation /></points>;
}
/** Decorative; respects reduced-motion by rendering nothing. */
export default function WaterParticles() {
  if (typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches) return null;
  return <Canvas camera={{ position: [0, 0, 6] }} dpr={[1, 1.5]} style={{ position: "absolute", inset: 0 }}><Points /></Canvas>;
}
