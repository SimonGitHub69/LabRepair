using CIE.MRTD.SDK.Util;
using System.Security.Cryptography;

namespace CIE.MRTD.SDK.Crypto
{
    internal class SHA256
    {
        public ByteArray Digest(byte[] data)
        {
            return HashAlgorithm.Create("SHA256").ComputeHash(data);
        }
    }
}
