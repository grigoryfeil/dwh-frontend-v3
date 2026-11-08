import "react";

declare module "react" {
  namespace JSX {
    interface IntrinsicElements {
      "dd-wireframe": React.DetailedHTMLProps<React.HTMLAttributes<HTMLElement>, HTMLElement> & { kind?: string; cx?: string; cy?: string; scale?: string };
    }
  }
}
