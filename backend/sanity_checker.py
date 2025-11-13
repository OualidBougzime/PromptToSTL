#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sanity checks optionnels pour valider les résultats après génération.
Ces checks vérifient que la géométrie générée correspond aux attentes.
"""

import logging
from typing import Optional, Dict, Any

log = logging.getLogger("cadamx.sanity")


class SanityChecker:
    """
    Vérifications post-génération pour s'assurer que la géométrie est correcte
    """

    def __init__(self):
        self.checks = {
            "pipe": self.check_pipe,
            "glass": self.check_glass,
            "spring": self.check_spring,
            "bowl": self.check_bowl,
            "vase": self.check_vase,
            "table": self.check_table,
        }
        log.info("✅ SanityChecker initialized")

    def check(self, result, object_type: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Exécute les sanity checks appropriés pour le type d'objet

        Args:
            result: L'objet CadQuery généré
            object_type: Type d'objet (pipe, glass, spring, etc.)
            params: Paramètres attendus (dimensions, etc.)

        Returns:
            Dict avec status et messages d'erreur/warning
        """
        if object_type not in self.checks:
            log.info(f"⚠️ No sanity check defined for type: {object_type}")
            return {"status": "skipped", "message": f"No check for {object_type}"}

        try:
            check_func = self.checks[object_type]
            return check_func(result, params or {})
        except Exception as e:
            log.error(f"❌ Sanity check failed for {object_type}: {e}")
            return {"status": "error", "message": str(e)}

    def check_pipe(self, result, params: Dict[str, Any]) -> Dict[str, Any]:
        """Vérifie qu'un tuyau a les bonnes dimensions et est creux"""
        try:
            bb = result.val().BoundingBox()

            expected_height = params.get("height", 150)
            expected_radius = params.get("outer_radius", 20)

            issues = []
            warnings = []

            # Vérifier la hauteur
            if abs(bb.zlen - expected_height) > 5:
                issues.append(f"Pipe height {bb.zlen:.1f} differs from expected {expected_height}")

            # Vérifier que le diamètre est cohérent
            max_diameter = max(bb.xlen, bb.ylen)
            if abs(max_diameter - 2*expected_radius) > 5:
                warnings.append(f"Pipe diameter {max_diameter:.1f} differs from expected {2*expected_radius}")

            # Vérifier qu'il y a des faces circulaires (rims)
            faces = result.faces("%Circle").vals()
            if len(faces) < 2:
                issues.append(f"Pipe should have at least 2 circular rims, found {len(faces)}")

            if issues:
                return {"status": "failed", "issues": issues, "warnings": warnings}
            elif warnings:
                return {"status": "warning", "warnings": warnings}
            else:
                return {"status": "passed", "message": "Pipe geometry looks correct"}

        except Exception as e:
            return {"status": "error", "message": f"Check failed: {e}"}

    def check_glass(self, result, params: Dict[str, Any]) -> Dict[str, Any]:
        """Vérifie qu'un verre a les bonnes dimensions et est creux"""
        try:
            bb = result.val().BoundingBox()

            expected_height = params.get("height", 100)
            expected_radius = params.get("outer_radius", 35)

            issues = []
            warnings = []

            # Vérifier la hauteur
            if abs(bb.zlen - expected_height) > 5:
                issues.append(f"Glass height {bb.zlen:.1f} differs from expected {expected_height}")

            # Vérifier le diamètre
            max_diameter = max(bb.xlen, bb.ylen)
            if abs(max_diameter - 2*expected_radius) > 5:
                warnings.append(f"Glass diameter {max_diameter:.1f} differs from expected {2*expected_radius}")

            # Vérifier qu'il y a des arêtes supérieures (rim)
            top_edges = result.edges(">Z").vals()
            if len(top_edges) == 0:
                issues.append("Glass should have top rim edges")

            if issues:
                return {"status": "failed", "issues": issues, "warnings": warnings}
            elif warnings:
                return {"status": "warning", "warnings": warnings}
            else:
                return {"status": "passed", "message": "Glass geometry looks correct"}

        except Exception as e:
            return {"status": "error", "message": f"Check failed: {e}"}

    def check_spring(self, result, params: Dict[str, Any]) -> Dict[str, Any]:
        """Vérifie qu'un ressort a une structure hélicoïdale"""
        try:
            bb = result.val().BoundingBox()

            expected_height = params.get("height", 80)
            expected_radius = params.get("radius", 20)

            issues = []
            warnings = []

            # Le ressort doit être plus haut que large
            if bb.zlen <= max(bb.xlen, bb.ylen):
                warnings.append(f"Spring height ({bb.zlen:.1f}) should be greater than width ({max(bb.xlen, bb.ylen):.1f})")

            # Vérifier la hauteur approximative
            if abs(bb.zlen - expected_height) > 10:
                warnings.append(f"Spring height {bb.zlen:.1f} differs from expected {expected_height}")

            # Vérifier le diamètre approximatif (2 * radius)
            max_diameter = max(bb.xlen, bb.ylen)
            if abs(max_diameter - 2*expected_radius) > 5:
                warnings.append(f"Spring diameter {max_diameter:.1f} differs from expected {2*expected_radius}")

            if issues:
                return {"status": "failed", "issues": issues, "warnings": warnings}
            elif warnings:
                return {"status": "warning", "warnings": warnings}
            else:
                return {"status": "passed", "message": "Spring geometry looks correct"}

        except Exception as e:
            return {"status": "error", "message": f"Check failed: {e}"}

    def check_bowl(self, result, params: Dict[str, Any]) -> Dict[str, Any]:
        """Vérifie qu'un bol est hémisphérique et creux"""
        try:
            bb = result.val().BoundingBox()

            expected_radius = params.get("radius", 40)

            issues = []
            warnings = []

            # Le bol doit être approximativement hémisphérique
            max_diameter = max(bb.xlen, bb.ylen)
            if abs(max_diameter - 2*expected_radius) > 5:
                warnings.append(f"Bowl diameter {max_diameter:.1f} differs from expected {2*expected_radius}")

            # La hauteur doit être approximativement le rayon (hémisphère)
            if abs(bb.zlen - expected_radius) > 10:
                warnings.append(f"Bowl height {bb.zlen:.1f} should be ~radius {expected_radius} for hemisphere")

            if issues:
                return {"status": "failed", "issues": issues, "warnings": warnings}
            elif warnings:
                return {"status": "warning", "warnings": warnings}
            else:
                return {"status": "passed", "message": "Bowl geometry looks correct"}

        except Exception as e:
            return {"status": "error", "message": f"Check failed: {e}"}

    def check_vase(self, result, params: Dict[str, Any]) -> Dict[str, Any]:
        """Vérifie qu'un vase a une forme loftée et est creux"""
        try:
            bb = result.val().BoundingBox()

            expected_height = params.get("height", 120)

            issues = []
            warnings = []

            # Vérifier la hauteur
            if abs(bb.zlen - expected_height) > 10:
                warnings.append(f"Vase height {bb.zlen:.1f} differs from expected {expected_height}")

            # Le vase doit avoir une certaine hauteur minimale
            if bb.zlen < 80:
                issues.append(f"Vase too short: {bb.zlen:.1f} mm")

            if issues:
                return {"status": "failed", "issues": issues, "warnings": warnings}
            elif warnings:
                return {"status": "warning", "warnings": warnings}
            else:
                return {"status": "passed", "message": "Vase geometry looks correct"}

        except Exception as e:
            return {"status": "error", "message": f"Check failed: {e}"}

    def check_table(self, result, params: Dict[str, Any]) -> Dict[str, Any]:
        """Vérifie qu'une table a un plateau et des pieds aux bons endroits"""
        try:
            bb = result.val().BoundingBox()

            expected_width = params.get("width", 200)
            expected_depth = params.get("depth", 100)
            expected_height = params.get("top_height", 120)

            issues = []
            warnings = []

            # Vérifier les dimensions du plateau
            if abs(bb.xlen - expected_width) > 10:
                warnings.append(f"Table width {bb.xlen:.1f} differs from expected {expected_width}")

            if abs(bb.ylen - expected_depth) > 10:
                warnings.append(f"Table depth {bb.ylen:.1f} differs from expected {expected_depth}")

            # Vérifier la hauteur totale
            if abs(bb.zlen - (expected_height + params.get("top_thickness", 15))) > 10:
                warnings.append(f"Table total height {bb.zlen:.1f} differs from expected")

            if issues:
                return {"status": "failed", "issues": issues, "warnings": warnings}
            elif warnings:
                return {"status": "warning", "warnings": warnings}
            else:
                return {"status": "passed", "message": "Table geometry looks correct"}

        except Exception as e:
            return {"status": "error", "message": f"Check failed: {e}"}


# Singleton instance
_sanity_checker = None

def get_sanity_checker() -> SanityChecker:
    """Retourne l'instance singleton du SanityChecker"""
    global _sanity_checker
    if _sanity_checker is None:
        _sanity_checker = SanityChecker()
    return _sanity_checker


__all__ = ["SanityChecker", "get_sanity_checker"]
