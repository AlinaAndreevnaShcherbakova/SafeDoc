import asyncio
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import quote

from fastapi.responses import Response

CONVERTIBLE_EXTENSIONS = {
    ".doc",
    ".docx",
    ".odt",
    ".rtf",
    ".ppt",
    ".pptx",
    ".odp",
    ".xls",
    ".xlsx",
    ".ods",
}

CONVERTIBLE_MIME_PREFIXES = (
    "application/vnd.openxmlformats-officedocument",
    "application/vnd.ms-",
    "application/msword",
    "application/vnd.oasis.opendocument",
    "application/rtf",
    "text/rtf",
)


def build_inline_content_disposition(filename: str) -> str:
    fallback = filename.encode("ascii", "ignore").decode("ascii").strip() or "preview"
    encoded = quote(filename, safe="")
    return f"inline; filename=\"{fallback}\"; filename*=UTF-8''{encoded}"


class PreviewService:
    def _needs_pdf_conversion(self, mime: str | None, filename: str) -> bool:
        ext = Path(filename or "").suffix.lower()
        if ext in CONVERTIBLE_EXTENSIONS:
            return True
        normalized_mime = (mime or "").lower()
        return normalized_mime.startswith(CONVERTIBLE_MIME_PREFIXES)

    def _convert_to_pdf_sync(self, data: bytes, filename: str) -> bytes | None:
        safe_name = Path(filename or "document").name
        suffix = Path(safe_name).suffix or ".bin"
        stem = Path(safe_name).stem or "document"

        with tempfile.TemporaryDirectory(prefix="safedoc-preview-") as tmpdir:
            temp_dir = Path(tmpdir)
            source_path = temp_dir / f"source{suffix}"
            source_path.write_bytes(data)

            command = [
                "soffice",
                "--headless",
                "--nologo",
                "--nofirststartwizard",
                "--convert-to",
                "pdf",
                "--outdir",
                str(temp_dir),
                str(source_path),
            ]

            try:
                subprocess.run(
                    command,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=40,
                )
            except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
                return None

            expected_pdf = temp_dir / f"source.pdf"
            if expected_pdf.exists():
                return expected_pdf.read_bytes()

            first_pdf = next(temp_dir.glob("*.pdf"), None)
            if first_pdf is None:
                return None
            return first_pdf.read_bytes()

    async def build_preview_payload(self, data: bytes, mime: str | None, filename: str) -> tuple[bytes, str, str]:
        if self._needs_pdf_conversion(mime=mime, filename=filename):
            converted_pdf = await asyncio.to_thread(self._convert_to_pdf_sync, data, filename)
            if converted_pdf is not None:
                pdf_name = f"{Path(filename).stem or 'preview'}.pdf"
                return converted_pdf, "application/pdf", pdf_name

        return data, mime or "application/octet-stream", filename

    async def build_preview_response(self, data: bytes, mime: str | None, filename: str) -> Response:
        payload, media_type, output_filename = await self.build_preview_payload(data=data, mime=mime, filename=filename)

        return Response(
            content=payload,
            media_type=media_type,
            headers={
                "Content-Disposition": build_inline_content_disposition(output_filename),
                "Cache-Control": "no-store",
            },
        )


preview_service = PreviewService()

