# 第三方组件与素材许可 / Third-Party Licenses & Notices

本程序（Exif-Renamer）在运行与打包分发时包含下列第三方组件。依其许可条款，
在此复现相应的版权声明与免责声明。本项目自身代码以 [MIT License](LICENSE) 授权。

> 说明：本文件仅用于满足组件的署名与声明义务，各组件版权归其各自作者所有，
> 本项目不对其作任何权利主张。

---

## 1. Pillow（PIL fork）

- 用途：读取图片基础 EXIF 与图像信息（回退引擎）
- 版本：12.3.0
- 许可：MIT-CMU License（HPND）
- 主页：https://python-pillow.org

```
The Python Imaging Library (PIL) is

    Copyright © 1997-2011 by Secret Labs AB
    Copyright © 1995-2011 by Fredrik Lundh and contributors

Pillow is the friendly PIL fork. It is

    Copyright © 2010 by Jeffrey 'Alex' Clark and contributors

Like PIL, Pillow is licensed under the open source MIT-CMU License:

By obtaining, using, and/or copying this software and/or its associated
documentation, you agree that you have read, understood, and will comply
with the following terms and conditions:

Permission to use, copy, modify and distribute this software and its
documentation for any purpose and without fee is hereby granted,
provided that the above copyright notice appears in all copies, and that
both that copyright notice and this permission notice appear in supporting
documentation, and that the name of Secret Labs AB or the author not be
used in advertising or publicity pertaining to distribution of the software
without specific, written prior permission.

SECRET LABS AB AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS
SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS.
IN NO EVENT SHALL SECRET LABS AB OR THE AUTHOR BE LIABLE FOR ANY SPECIAL,
INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE
OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
PERFORMANCE OF THIS SOFTWARE.
```

> Pillow 的官方分发还内嵌若干原生库（如 brotli、FreeType、libjpeg-turbo、
> libwebp、zlib、OpenJPEG 等），各自适用不同的开源许可（BSD / zlib / IJG 等）。
> 这些组件的完整许可清单见上游 Pillow 仓库的 `LICENSE` 文件：
> https://github.com/python-pillow/Pillow/blob/main/LICENSE

---

## 2. exifread

- 用途：解析 EXIF/XMP 拍摄时间（RAW/HEIC 解析的主要引擎）
- 版本：3.5.1
- 许可：BSD 3-Clause
- 主页：https://github.com/ianare/exif-py

```
Copyright (c) 2002-2007 Gene Cash
Copyright (c) 2007-2025 Ianaré Sévi and contributors

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions
are met:

 1. Redistributions of source code must retain the above copyright
    notice, this list of conditions and the following disclaimer.

 2. Redistributions in binary form must reproduce the above
    copyright notice, this list of conditions and the following
    disclaimer in the documentation and/or other materials provided
    with the distribution.

 3. Neither the name of the authors nor the names of its contributors
    may be used to endorse or promote products derived from this
    software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```

---

## 3. PyInstaller（打包工具）

- 用途：将本程序打包为独立 exe（仅构建期使用，其 bootloader 会被嵌入产物）
- 版本：6.22.2
- 许可：GPL-2.0-or-later，附带 Bootloader Exception
- 主页：https://pyinstaller.org

PyInstaller 的 **Bootloader Exception** 明确授予将编译后的 bootloader 及相关文件
嵌入其他程序并无限制分发该组合产物的权利，因此本程序的 exe 不因嵌入 bootloader
而受 GPL 约束。相关条款原文：

```
Bootloader Exception
--------------------

In addition to the permissions in the GNU General Public License, the
authors give you unlimited permission to link or embed compiled bootloader
and related files into combinations with other programs, and to distribute
those combinations without any restriction coming from the use of those
files. (The General Public License restrictions do apply in other respects;
for example, they cover modification of the files, and distribution when
not linked into a combined executable.)
```

> PyInstaller 的 run-time hooks（`PyInstaller/hooks/rthooks`，会被嵌入产物）
> 另行以 Apache License 2.0 授权。完整条款见上游仓库：
> https://github.com/pyinstaller/pyinstaller/blob/develop/COPYING.txt

---

## 4. pyinstaller-hooks-contrib（构建期依赖）

- 用途：为第三方库提供 PyInstaller 补充 hooks（仅构建期使用，不随产物分发）
- 版本：2026.7
- 许可：Apache License 2.0
- 主页：https://github.com/pyinstaller/pyinstaller-hooks-contrib
- 完整条款：https://github.com/pyinstaller/pyinstaller-hooks-contrib/blob/master/LICENSE

---

## 5. 本项目自有素材

- `assets/icon.png` / `assets/icon.ico`：由 AI 生成，作为本项目图标使用。
- `images/*.png`：本程序界面截图。
- 上述素材均为本项目自用素材，不包含第三方版权内容。
