using CIE.MRTD.SDK.Util;
using System.Security.Cryptography;

namespace CIE.MRTD.SDK.Crypto
{
    internal class SHA1
    {
        public ByteArray Digest(byte[] data)
        {
            return HashAlgorithm.Create("SHA1").ComputeHash(data);
        }
    }
}
