# 第三方组件与素材许可 / Third-Party Licenses & Notices

本程序（Exif-Renamer）在运行与打包分发时包含下列第三方组件。依其许可条款，在此复现相应的版权声明与免责声明。本项目自身代码以 [MIT License](LICENSE) 授权（该文件另含关于 AI 辅助生成内容的说明）。

> 说明：本文件仅用于满足组件的署名与声明义务，各组件版权归其各自作者所有，本项目不对其作任何权利主张。
>
> 表中版本为整理时构建环境中的实际版本；本项目依赖只设下限、不锁定版本（见 `requirements.txt`），发布产物可能包含更新的上游版本，届时请以各上游仓库的许可文本为准。

| 组件 | 版本 | 许可 | 随产物分发 |
|---|---|---|---|
| Pillow | 12.3.0 | MIT-CMU（HPND） | 是（两个 exe） |
| exifread | 3.5.1 | BSD 3-Clause | 是（两个 exe） |
| Python 运行时 | 3.14.7 | PSF-2.0 | 是（两个 exe） |
| Tcl/Tk | 9.0 | BSD 风格（Tcl/Tk License） | 是（两个 exe，tkinter） |
| PyInstaller | 6.22.2 | GPL-2.0-or-later + Bootloader Exception | 仅 bootloader |
| pyinstaller-hooks-contrib | 2026.7 | GPL-2.0-or-later / Apache-2.0 | 否（仅构建期） |

> 本程序的两个工具（`exif_renamer-<时间戳>.exe` 与 `exif_debugger-<时间戳>.exe`）均为 tkinter 图形界面程序，因此各自都包含 Python 运行时与 Tcl/Tk。

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

> Pillow 的官方分发还内嵌若干原生库（如 brotli、FreeType、libjpeg-turbo、libwebp、zlib、OpenJPEG 等），各自适用不同的开源许可（BSD / zlib / IJG 等）。这些组件的完整许可清单见上游 Pillow 仓库的 `LICENSE` 文件：https://github.com/python-pillow/Pillow/blob/main/LICENSE

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

## 3. Python 运行时

- 用途：本程序由 PyInstaller 打包，Python 解释器（3.14.7）被嵌入两个 exe
- 许可：Python Software Foundation License Version 2（PSF-2.0）
- 版权：Copyright (c) 2001-2023 Python Software Foundation; All Rights Reserved
- 主页：https://www.python.org

```
PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2
--------------------------------------------

1. This LICENSE AGREEMENT is between the Python Software Foundation
("PSF"), and the Individual or Organization ("Licensee") accessing and
otherwise using this software ("Python") in source or binary form and
its associated documentation.

2. Subject to the terms and conditions of this License Agreement, PSF hereby
grants Licensee a nonexclusive, royalty-free, world-wide license to reproduce,
analyze, test, perform and/or display publicly, prepare derivative works,
distribute, and otherwise use Python alone or in any derivative version,
provided, however, that PSF's License Agreement and PSF's notice of copyright,
i.e., "Copyright (c) 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010,
2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023 Python Software Foundation;
All Rights Reserved" are retained in Python alone or in any derivative version
prepared by Licensee.

3. In the event Licensee prepares a derivative work that is based on
or incorporates Python or any part thereof, and wants to make
the derivative work available to others as provided herein, then
Licensee hereby agrees to include in any such work a brief summary of
the changes made to Python.

4. PSF is making Python available to Licensee on an "AS IS"
basis.  PSF MAKES NO REPRESENTATIONS OR WARRANTIES, EXPRESS OR
IMPLIED.  BY WAY OF EXAMPLE, BUT NOT LIMITATION, PSF MAKES NO AND
DISCLAIMS ANY REPRESENTATION OR WARRANTY OF MERCHANTABILITY OR FITNESS
FOR ANY PARTICULAR PURPOSE OR THAT THE USE OF PYTHON WILL NOT
INFRINGE ANY THIRD PARTY RIGHTS.

5. PSF SHALL NOT BE LIABLE TO LICENSEE OR ANY OTHER USERS OF PYTHON
FOR ANY INCIDENTAL, SPECIAL, OR CONSEQUENTIAL DAMAGES OR LOSS AS
A RESULT OF MODIFYING, DISTRIBUTING, OR OTHERWISE USING PYTHON,
OR ANY DERIVATIVE THEREOF, EVEN IF ADVISED OF THE POSSIBILITY THEREOF.

6. This License Agreement will automatically terminate upon a material
breach of its terms and conditions.

7. Nothing in this License Agreement shall be deemed to create any
relationship of agency, partnership, or joint venture between PSF and
Licensee.  This License Agreement does not grant permission to use PSF
trademarks or trade name in a trademark sense to endorse or promote
products or services of Licensee, or any third party.

8. By copying, installing or otherwise using Python, Licensee
agrees to be bound by the terms and conditions of this License
Agreement.
```

> Python 发行版自身还内含其他组件与其历史许可条款（BeOpen、CNRI、CWI 等），完整清单见 CPython 仓库的 `LICENSE` 文件：https://github.com/python/cpython/blob/main/LICENSE

---

## 4. Tcl/Tk

- 用途：两个工具（`exif_renamer.py`、`exif_debugger.py`）的 tkinter 界面与绘图底层
- 版本：Tcl/Tk 9.0（随 Python 3.14 分发）
- 许可：BSD 风格（Tcl/Tk License）

```
This software is copyrighted by the Regents of the University of
California, Sun Microsystems, Inc., Scriptics Corporation, ActiveState
Corporation, Apple Inc. and other parties.  The following terms apply to
all files associated with the software unless explicitly disclaimed in
individual files.

The authors hereby grant permission to use, copy, modify, distribute,
and license this software and its documentation for any purpose, provided
that existing copyright notices are retained in all copies and that this
notice is included verbatim in any distributions. No written agreement,
license, or royalty fee is required for any of the authorized uses.
Modifications to this software may be copyrighted by their authors
and need not follow the licensing terms described here, provided that
the new terms are clearly indicated on the first page of each file where
they apply.

IN NO EVENT SHALL THE AUTHORS OR DISTRIBUTORS BE LIABLE TO ANY PARTY
FOR DIRECT, INDIRECT, SPECIAL, INCIDENTAL, OR CONSEQUENTIAL DAMAGES
ARISING OUT OF THE USE OF THIS SOFTWARE, ITS DOCUMENTATION, OR ANY
DERIVATIVES THEREOF, EVEN IF THE AUTHORS HAVE BEEN ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.

THE AUTHORS AND DISTRIBUTORS SPECIFICALLY DISCLAIM ANY WARRANTIES,
INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.  THIS SOFTWARE
IS PROVIDED ON AN "AS IS" BASIS, AND THE AUTHORS AND DISTRIBUTORS HAVE
NO OBLIGATION TO PROVIDE MAINTENANCE, SUPPORT, UPDATES, ENHANCEMENTS, OR
MODIFICATIONS.

GOVERNMENT USE: If you are acquiring this software on behalf of the
U.S. government, the Government shall have only "Restricted Rights"
in the software and related documentation as defined in the Federal
Acquisition Regulations (FARs) in Clause 52.227.19 (c) (2).  If you
are acquiring the software on behalf of the Department of Defense, the
software shall be classified as "Commercial Computer Software" and the
Government shall have only "Restricted Rights" as defined in Clause
252.227-7013 (b) (3) of DFARs.  Notwithstanding the foregoing, the
authors grant the U.S. Government and others acting in its behalf
permission to use and distribute the software in accordance with the
terms specified in this license.
```

---

## 5. PyInstaller（打包工具）

- 用途：将本程序打包为独立 exe（仅构建期使用，其 bootloader 会被嵌入产物）
- 版本：6.22.2
- 许可：GPL-2.0-or-later，附带 Bootloader Exception
- 主页：https://pyinstaller.org

PyInstaller 的 **Bootloader Exception** 明确授予将编译后的 bootloader 及相关文件嵌入其他程序并无限制分发该组合产物的权利，因此本程序的 exe 不因嵌入 bootloader 而受 GPL 约束。相关条款原文：

```
Bootloader Exception
---------------------

In addition to the permissions in the GNU General Public License, the
authors give you unlimited permission to link or embed compiled bootloader
and related files into combinations with other programs, and to distribute
those combinations without any restriction coming from the use of those
files. (The General Public License restrictions do apply in other respects;
for example, they cover modification of the files, and distribution when
not linked into a combined executable.)
```

> PyInstaller 的 run-time hooks（`PyInstaller/hooks/rthooks`，会被嵌入产物）另行以 Apache License 2.0 授权。完整条款见上游仓库：https://github.com/pyinstaller/pyinstaller/blob/develop/COPYING.txt

---

## 6. pyinstaller-hooks-contrib（构建期依赖）

| 组件 | 版本 | 许可 | 上游 |
|---|---|---|---|
| pyinstaller-hooks-contrib | 2026.7 | GPL-2.0-or-later（stdhooks）/ Apache-2.0（runtime hooks） | https://github.com/pyinstaller/pyinstaller-hooks-contrib |

该包是 PyInstaller 的官方依赖（由 `pip install pyinstaller` 自动带入），不单独使用，仅提供社区维护的补充 hooks。本项目的依赖不需要它：Pillow 的 hook 由 PyInstaller 自身内置（`PyInstaller/hooks/hook-PIL*.py`），exifread 为纯 Python、无需 hook；其 `rthooks`（runtime hooks，若触发则会随 exe 分发）在本项目依赖上均未触发。因此本程序的产物中不含该包的代码，不产生 GPL 分发义务。

> PyInstaller 在构建期还会带入 `altgraph`、`pefile`、`pywin32-ctypes`、`packaging`、`setuptools` 等依赖，同样只在构建期使用，不随产物分发。

---

## 7. 本项目自有素材

- `assets/icon.png` / `assets/icon.ico`：本项目图标，由 AI 生成，作为本项目自用素材。相关来源与免责说明见 [LICENSE](LICENSE) 末尾的附加说明。
- `images/*.png`：README 中使用的界面截图，仅用于仓库展示，不在本程序的分发包内。
