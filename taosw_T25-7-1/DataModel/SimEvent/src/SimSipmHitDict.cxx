// Do NOT change. Changes will be lost next time file is generated

#define R__DICTIONARY_FILENAME dItmpdIbdIjunodOihepdOacdOcndIel9_amd64_gcc11dIReleasedIJ25dO7dO1dItaoswdIbuilddIDataModeldISimEventdIsrcdISimSipmHitDict
#define R__NO_DEPRECATION

/*******************************************************************/
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#define G__DICTIONARY
#include "ROOT/RConfig.hxx"
#include "TClass.h"
#include "TDictAttributeMap.h"
#include "TInterpreter.h"
#include "TROOT.h"
#include "TBuffer.h"
#include "TMemberInspector.h"
#include "TInterpreter.h"
#include "TVirtualMutex.h"
#include "TError.h"

#ifndef G__ROOT
#define G__ROOT
#endif

#include "RtypesImp.h"
#include "TIsAProxy.h"
#include "TFileMergeInfo.h"
#include <algorithm>
#include "TCollectionProxyInfo.h"
/*******************************************************************/

#include "TDataMember.h"

// Header files passed as explicit arguments
#include "/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/SimEvent/Event/SimSipmHit.h"

// Header files passed via #pragma extra_include

// The generated code does not explicitly qualify STL entities
namespace std {} using namespace std;

namespace ROOT {
   static void *new_TaocLcLSimSipmHit(void *p = nullptr);
   static void *newArray_TaocLcLSimSipmHit(Long_t size, void *p);
   static void delete_TaocLcLSimSipmHit(void *p);
   static void deleteArray_TaocLcLSimSipmHit(void *p);
   static void destruct_TaocLcLSimSipmHit(void *p);

   // Function generating the singleton type initializer
   static TGenericClassInfo *GenerateInitInstanceLocal(const ::Tao::SimSipmHit*)
   {
      ::Tao::SimSipmHit *ptr = nullptr;
      static ::TVirtualIsAProxy* isa_proxy = new ::TInstrumentedIsAProxy< ::Tao::SimSipmHit >(nullptr);
      static ::ROOT::TGenericClassInfo 
         instance("Tao::SimSipmHit", ::Tao::SimSipmHit::Class_Version(), "Event/SimSipmHit.h", 10,
                  typeid(::Tao::SimSipmHit), ::ROOT::Internal::DefineBehavior(ptr, ptr),
                  &::Tao::SimSipmHit::Dictionary, isa_proxy, 4,
                  sizeof(::Tao::SimSipmHit) );
      instance.SetNew(&new_TaocLcLSimSipmHit);
      instance.SetNewArray(&newArray_TaocLcLSimSipmHit);
      instance.SetDelete(&delete_TaocLcLSimSipmHit);
      instance.SetDeleteArray(&deleteArray_TaocLcLSimSipmHit);
      instance.SetDestructor(&destruct_TaocLcLSimSipmHit);
      return &instance;
   }
   TGenericClassInfo *GenerateInitInstance(const ::Tao::SimSipmHit*)
   {
      return GenerateInitInstanceLocal(static_cast<::Tao::SimSipmHit*>(nullptr));
   }
   // Static variable to force the class initialization
   static ::ROOT::TGenericClassInfo *_R__UNIQUE_DICT_(Init) = GenerateInitInstanceLocal(static_cast<const ::Tao::SimSipmHit*>(nullptr)); R__UseDummy(_R__UNIQUE_DICT_(Init));
} // end of namespace ROOT

namespace Tao {
//______________________________________________________________________________
atomic_TClass_ptr SimSipmHit::fgIsA(nullptr);  // static to hold class pointer

//______________________________________________________________________________
const char *SimSipmHit::Class_Name()
{
   return "Tao::SimSipmHit";
}

//______________________________________________________________________________
const char *SimSipmHit::ImplFileName()
{
   return ::ROOT::GenerateInitInstanceLocal((const ::Tao::SimSipmHit*)nullptr)->GetImplFileName();
}

//______________________________________________________________________________
int SimSipmHit::ImplFileLine()
{
   return ::ROOT::GenerateInitInstanceLocal((const ::Tao::SimSipmHit*)nullptr)->GetImplFileLine();
}

//______________________________________________________________________________
TClass *SimSipmHit::Dictionary()
{
   fgIsA = ::ROOT::GenerateInitInstanceLocal((const ::Tao::SimSipmHit*)nullptr)->GetClass();
   return fgIsA;
}

//______________________________________________________________________________
TClass *SimSipmHit::Class()
{
   if (!fgIsA.load()) { R__LOCKGUARD(gInterpreterMutex); fgIsA = ::ROOT::GenerateInitInstanceLocal((const ::Tao::SimSipmHit*)nullptr)->GetClass(); }
   return fgIsA;
}

} // namespace Tao
namespace Tao {
//______________________________________________________________________________
void SimSipmHit::Streamer(TBuffer &R__b)
{
   // Stream an object of class Tao::SimSipmHit.

   if (R__b.IsReading()) {
      R__b.ReadClassBuffer(Tao::SimSipmHit::Class(),this);
   } else {
      R__b.WriteClassBuffer(Tao::SimSipmHit::Class(),this);
   }
}

} // namespace Tao
namespace ROOT {
   // Wrappers around operator new
   static void *new_TaocLcLSimSipmHit(void *p) {
      return  p ? new(p) ::Tao::SimSipmHit : new ::Tao::SimSipmHit;
   }
   static void *newArray_TaocLcLSimSipmHit(Long_t nElements, void *p) {
      return p ? new(p) ::Tao::SimSipmHit[nElements] : new ::Tao::SimSipmHit[nElements];
   }
   // Wrapper around operator delete
   static void delete_TaocLcLSimSipmHit(void *p) {
      delete (static_cast<::Tao::SimSipmHit*>(p));
   }
   static void deleteArray_TaocLcLSimSipmHit(void *p) {
      delete [] (static_cast<::Tao::SimSipmHit*>(p));
   }
   static void destruct_TaocLcLSimSipmHit(void *p) {
      typedef ::Tao::SimSipmHit current_t;
      (static_cast<current_t*>(p))->~current_t();
   }
} // end of namespace ROOT for class ::Tao::SimSipmHit

namespace ROOT {
   static TClass *vectorlETaocLcLSimSipmHitgR_Dictionary();
   static void vectorlETaocLcLSimSipmHitgR_TClassManip(TClass*);
   static void *new_vectorlETaocLcLSimSipmHitgR(void *p = nullptr);
   static void *newArray_vectorlETaocLcLSimSipmHitgR(Long_t size, void *p);
   static void delete_vectorlETaocLcLSimSipmHitgR(void *p);
   static void deleteArray_vectorlETaocLcLSimSipmHitgR(void *p);
   static void destruct_vectorlETaocLcLSimSipmHitgR(void *p);

   // Function generating the singleton type initializer
   static TGenericClassInfo *GenerateInitInstanceLocal(const vector<Tao::SimSipmHit>*)
   {
      vector<Tao::SimSipmHit> *ptr = nullptr;
      static ::TVirtualIsAProxy* isa_proxy = new ::TIsAProxy(typeid(vector<Tao::SimSipmHit>));
      static ::ROOT::TGenericClassInfo 
         instance("vector<Tao::SimSipmHit>", -2, "vector", 389,
                  typeid(vector<Tao::SimSipmHit>), ::ROOT::Internal::DefineBehavior(ptr, ptr),
                  &vectorlETaocLcLSimSipmHitgR_Dictionary, isa_proxy, 4,
                  sizeof(vector<Tao::SimSipmHit>) );
      instance.SetNew(&new_vectorlETaocLcLSimSipmHitgR);
      instance.SetNewArray(&newArray_vectorlETaocLcLSimSipmHitgR);
      instance.SetDelete(&delete_vectorlETaocLcLSimSipmHitgR);
      instance.SetDeleteArray(&deleteArray_vectorlETaocLcLSimSipmHitgR);
      instance.SetDestructor(&destruct_vectorlETaocLcLSimSipmHitgR);
      instance.AdoptCollectionProxyInfo(TCollectionProxyInfo::Generate(TCollectionProxyInfo::Pushback< vector<Tao::SimSipmHit> >()));

      instance.AdoptAlternate(::ROOT::AddClassAlternate("vector<Tao::SimSipmHit>","std::vector<Tao::SimSipmHit, std::allocator<Tao::SimSipmHit> >"));
      return &instance;
   }
   // Static variable to force the class initialization
   static ::ROOT::TGenericClassInfo *_R__UNIQUE_DICT_(Init) = GenerateInitInstanceLocal(static_cast<const vector<Tao::SimSipmHit>*>(nullptr)); R__UseDummy(_R__UNIQUE_DICT_(Init));

   // Dictionary for non-ClassDef classes
   static TClass *vectorlETaocLcLSimSipmHitgR_Dictionary() {
      TClass* theClass =::ROOT::GenerateInitInstanceLocal(static_cast<const vector<Tao::SimSipmHit>*>(nullptr))->GetClass();
      vectorlETaocLcLSimSipmHitgR_TClassManip(theClass);
   return theClass;
   }

   static void vectorlETaocLcLSimSipmHitgR_TClassManip(TClass* ){
   }

} // end of namespace ROOT

namespace ROOT {
   // Wrappers around operator new
   static void *new_vectorlETaocLcLSimSipmHitgR(void *p) {
      return  p ? ::new(static_cast<::ROOT::Internal::TOperatorNewHelper*>(p)) vector<Tao::SimSipmHit> : new vector<Tao::SimSipmHit>;
   }
   static void *newArray_vectorlETaocLcLSimSipmHitgR(Long_t nElements, void *p) {
      return p ? ::new(static_cast<::ROOT::Internal::TOperatorNewHelper*>(p)) vector<Tao::SimSipmHit>[nElements] : new vector<Tao::SimSipmHit>[nElements];
   }
   // Wrapper around operator delete
   static void delete_vectorlETaocLcLSimSipmHitgR(void *p) {
      delete (static_cast<vector<Tao::SimSipmHit>*>(p));
   }
   static void deleteArray_vectorlETaocLcLSimSipmHitgR(void *p) {
      delete [] (static_cast<vector<Tao::SimSipmHit>*>(p));
   }
   static void destruct_vectorlETaocLcLSimSipmHitgR(void *p) {
      typedef vector<Tao::SimSipmHit> current_t;
      (static_cast<current_t*>(p))->~current_t();
   }
} // end of namespace ROOT for class vector<Tao::SimSipmHit>

namespace {
  void TriggerDictionaryInitialization_SimSipmHitDict_Impl() {
    static const char* headers[] = {
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/SimEvent/Event/SimSipmHit.h",
nullptr
    };
    static const char* includePaths[] = {
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/build/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/Python/3.11.10/include/python3.11",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/Boost/1.85.0",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/log4cpp/1.1.3/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/ROOT/6.30.08/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/CLHEP/2.4.7.1/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J24.2.0/ExternalLibs/CLHEP/2.4.7.1/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/Geant4/10.04.p02.juno/include/geant4",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/HepMC/2.06.11/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/genie/3.04.02/include/GENIE",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/frontier/2.10.2/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/mysql-connector-c/6.1.9/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/mysql-connector-cpp/1.1.12/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/libyaml/0.2.4/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/libonnxruntime/1.17.3/include/onnxruntime",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/libonnxruntime/1.17.3/include/onnxruntime/core/session",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/nuwro/21.09.2/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/SimEvent",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/SimEvent/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/build/DataModel/SimEvent",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/junosw/InstallArea/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/junosw/InstallArea/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.4.0/ExternalLibs/ROOT/6.30.08/include/",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/build/DataModel/SimEvent/",
nullptr
    };
    static const char* fwdDeclCode = R"DICTFWDDCLS(
#line 1 "SimSipmHitDict dictionary forward declarations' payload"
#pragma clang diagnostic ignored "-Wkeyword-compat"
#pragma clang diagnostic ignored "-Wignored-attributes"
#pragma clang diagnostic ignored "-Wreturn-type-c-linkage"
extern int __Cling_AutoLoading_Map;
namespace Tao{class __attribute__((annotate("$clingAutoload$/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/SimEvent/Event/SimSipmHit.h")))  SimSipmHit;}
namespace std{template <typename _Tp> class __attribute__((annotate("$clingAutoload$bits/allocator.h")))  __attribute__((annotate("$clingAutoload$string")))  allocator;
}
)DICTFWDDCLS";
    static const char* payloadCode = R"DICTPAYLOAD(
#line 1 "SimSipmHitDict dictionary payload"


#define _BACKWARD_BACKWARD_WARNING_H
// Inline headers
#include "/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/SimEvent/Event/SimSipmHit.h"

#undef  _BACKWARD_BACKWARD_WARNING_H
)DICTPAYLOAD";
    static const char* classesHeaders[] = {
"Tao::SimSipmHit", payloadCode, "@",
nullptr
};
    static bool isInitialized = false;
    if (!isInitialized) {
      TROOT::RegisterModule("SimSipmHitDict",
        headers, includePaths, payloadCode, fwdDeclCode,
        TriggerDictionaryInitialization_SimSipmHitDict_Impl, {}, classesHeaders, /*hasCxxModule*/false);
      isInitialized = true;
    }
  }
  static struct DictInit {
    DictInit() {
      TriggerDictionaryInitialization_SimSipmHitDict_Impl();
    }
  } __TheDictionaryInitializer;
}
void TriggerDictionaryInitialization_SimSipmHitDict() {
  TriggerDictionaryInitialization_SimSipmHitDict_Impl();
}
