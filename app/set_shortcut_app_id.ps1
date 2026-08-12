param(
    [Parameter(Mandatory = $true)]
    [string]$ShortcutPath,

    [string]$AppUserModelId = "Avtoreya.Desktop"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $ShortcutPath)) {
    exit 0
}

if (-not ("Avtoreya.ShortcutProperties" -as [type])) {
    Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
using System.Runtime.InteropServices.ComTypes;

namespace Avtoreya
{
    [StructLayout(LayoutKind.Sequential, Pack = 4)]
    internal struct PropertyKey
    {
        public Guid FormatId;
        public uint PropertyId;

        public PropertyKey(Guid formatId, uint propertyId)
        {
            FormatId = formatId;
            PropertyId = propertyId;
        }
    }

    [StructLayout(LayoutKind.Explicit, Size = 24)]
    internal struct PropVariant
    {
        [FieldOffset(0)] public ushort ValueType;
        [FieldOffset(8)] public IntPtr PointerValue;

        public static PropVariant FromString(string value)
        {
            return new PropVariant
            {
                ValueType = 31, // VT_LPWSTR
                PointerValue = Marshal.StringToCoTaskMemUni(value)
            };
        }
    }

    [ComImport]
    [Guid("886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99")]
    [InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    internal interface IPropertyStore
    {
        uint GetCount();
        PropertyKey GetAt(uint propertyIndex);
        void GetValue(ref PropertyKey key, out PropVariant value);
        void SetValue(ref PropertyKey key, ref PropVariant value);
        void Commit();
    }

    [ComImport]
    [Guid("00021401-0000-0000-C000-000000000046")]
    internal class ShellLink
    {
    }

    public static class ShortcutProperties
    {
        [DllImport("ole32.dll")]
        private static extern int PropVariantClear(ref PropVariant value);

        public static void SetAppUserModelId(string shortcutPath, string appUserModelId)
        {
            object shellLink = new ShellLink();
            try
            {
                IPersistFile persistFile = (IPersistFile)shellLink;
                persistFile.Load(shortcutPath, 2); // STGM_READWRITE
                IPropertyStore propertyStore = (IPropertyStore)shellLink;
                PropertyKey key = new PropertyKey(
                    new Guid("9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3"), 5);
                PropVariant value = PropVariant.FromString(appUserModelId);
                try
                {
                    propertyStore.SetValue(ref key, ref value);
                    propertyStore.Commit();
                    persistFile.Save(shortcutPath, true);
                }
                finally
                {
                    PropVariantClear(ref value);
                }
            }
            finally
            {
                Marshal.FinalReleaseComObject(shellLink);
            }
        }
    }
}
"@
}

$resolved = (Resolve-Path -LiteralPath $ShortcutPath).Path
[Avtoreya.ShortcutProperties]::SetAppUserModelId($resolved, $AppUserModelId)
