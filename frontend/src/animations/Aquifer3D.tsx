import { Canvas, useFrame } from "@react-three/fiber"; import { useRef } from "react"; import * as THREE from "three";
/** Schematic (not data-driven) aquifer: freshwater lens above a saltwater wedge that advances with `intrusion` (0–1). */
function Scene({ intrusion }: { intrusion: number }) {
  const wedge = useRef<THREE.Mesh>(null);
  useFrame(() => { if (wedge.current) wedge.current.scale.x += (intrusion - wedge.current.scale.x) * .05; });
  return (<><ambientLight intensity={.8} /><directionalLight position={[3, 5, 4]} />
    <mesh position={[0, -.2, 0]}><boxGeometry args={[6, 1.6, 2]} /><meshStandardMaterial color="#38BDF8" transparent opacity={.5} /></mesh>
    <mesh ref={wedge} position={[2, -.7, 0]} scale={[.3, 1, 1]}><boxGeometry args={[3, .6, 2]} /><meshStandardMaterial color="#DC2626" transparent opacity={.55} /></mesh>
    <mesh position={[0, .9, 0]}><boxGeometry args={[6, .4, 2]} /><meshStandardMaterial color="#8d6e4a" /></mesh></>);
}
export default function Aquifer3D({ intrusion = .3 }: { intrusion?: number }) {
  return <div className="h-48 rounded-xl overflow-hidden bg-slate-900"><Canvas camera={{ position: [0, 1, 6], fov: 45 }}><Scene intrusion={intrusion} /></Canvas></div>;
}
