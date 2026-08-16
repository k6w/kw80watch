# Firmware request to Huawo — draft

**To:** service@huawo-wear.com
**Cc:** limingxing@huawo-wear.com
**Subject:** Firmware image request — HA01_HW (KW80), V1.0.1R0.2T0.5H0.2B01

Send whichever version you prefer. The Chinese one will probably get a faster
reply — they are based in Guangzhou. You can send both in one message (Chinese
first, English below), which is normal practice.

Everything stated below is true. Do not add claims about being a business
partner or reseller — if they ask what it's for, the honest answer works fine
and a false one would end the conversation badly.

---

## Chinese version

> 您好，
>
> 我是一名 KW80 智能手表的用户，该设备使用 HaWoFit App 配对。
>
> 我想请问是否可以提供我这台设备对应的固件文件（.bin），用于本机的恢复与
> 重新烧录。
>
> 设备信息：
>
> - 产品型号 / Product code：**HA01_HW**
> - 设备名称：KW80
> - 当前固件版本：**V1.0.1R0.2T0.5H0.2B01**
> - 屏幕：368 × 448
>
> 我注意到 HaWoFit 的升级接口
> （`api/v1/devices/upgrades`）对该型号没有返回任何固件包，因此想直接向贵司
> 咨询。
>
> 如果需要提供购买凭证或设备序列号，我可以补充。
>
> 感谢您的帮助！
>
> 此致

---

## English version

> Hello,
>
> I am an owner of a KW80 smartwatch, which pairs with the HaWoFit app.
>
> I would like to ask whether it is possible to obtain the firmware image
> (.bin) for my device, for recovery and re-flashing of this unit.
>
> Device details:
>
> - Product code: **HA01_HW**
> - Device name: KW80
> - Current firmware: **V1.0.1R0.2T0.5H0.2B01**
> - Display: 368 × 448
>
> I noticed that the HaWoFit upgrade endpoint (`api/v1/devices/upgrades`)
> returns no firmware package for this product code, so I am contacting you
> directly.
>
> I am happy to provide proof of purchase or the device serial number if that
> helps.
>
> Thank you for your time.
>
> Best regards,

---

## Notes

**Optional extra detail.** Your device serial is `HWHA0122032101002563`. Include
it only if they ask — it identifies your specific unit and there is no reason to
volunteer it up front.

**What a good outcome looks like.** Any `.bin` for HA01/HA01_HW at any version.
Even a *different* build from yours (for example the `V1.0.0R0.1T0.5H0.2B02`
seen on another user's watch) would be enormously useful: it would give a real
vector table and flash map, settling the Ambiq question immediately and
providing a restore path.

**Realistic odds: low.** Huawo is a B2B ODM — their site has no consumer
downloads, and firmware is normally handled through brand customers rather than
end users. But they are the only party that definitely holds the file, and the
request costs nothing.

**If they decline**, a reasonable follow-up is to ask whether the brand that
sold your watch (KingWear) can request it on your behalf, since brand customers
are their normal support channel.
